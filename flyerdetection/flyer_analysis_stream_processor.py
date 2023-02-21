#imports
import datetime
from io import BytesIO
import numpy as np, pandas as pd
from PIL import Image
from openmsistream import DataFileStreamProcessor
from .flyer_detection import Flyer_Detection

class FlyerAnalysisStreamProcessor(DataFileStreamProcessor) :
    """
    A class to run flyer analysis for all .bmp images in a topic and add their results to an ouput file
    """

    def __init__(self,config_file,topic_name,output_dir,**kwargs) :
        super().__init__(config_file,topic_name,output_dir,**kwargs)
        self._output_file = self._output_dir/'flyer_analysis_results.csv'

    def _process_downloaded_data_file(self,datafile,lock) :
        """
        Run the flyer analysis on the downloaded data file

        returns None if processing was successful, an Exception otherwise
        """
        if not datafile.filename.endswith('.bmp') :
            return None
        try :
            analyzer = Flyer_Detection()
            img = np.asarray(Image.open(BytesIO(datafile.bytestring)))
            filtered_image=analyzer.filter_image(img) 
            result = analyzer.radius_from_lslm(
                filtered_image,
                datafile.relative_filepath,
                self._output_dir,
                min_radius=0,
                max_radius=np.inf,
                save_output_file=False,
            )
            data = vars(result)
            data_frame = pd.DataFrame([data])
            with lock :
                if self._output_file.is_file() :
                    data_frame.to_csv(self._output_file,mode='a',index=False,header=False)
                else :
                    data_frame.to_csv(self._output_file,mode='w',index=False,header=True)
        except Exception as exc :
            return exc
        return None

    @classmethod
    def run_from_command_line(cls,args=None) :
        """
        Run the stream-processed analysis code from the command line
        """
        #make the argument parser
        parser = cls.get_argument_parser()
        args = parser.parse_args(args=args)
        #make the stream processor
        flyer_analysis = cls(args.config,args.topic_name,
                             output_dir=args.output_dir,
                             n_threads=args.n_threads,
                             update_secs=args.update_seconds,
                             consumer_group_id=args.consumer_group_id)
        #start the processor running (returns total number of messages read, processed, and names of processed files)
        run_start = datetime.datetime.now()
        msg = f'Listening to the {args.topic_name} topic for flyer image files to analyze'
        flyer_analysis.logger.info(msg)
        n_read,n_processed,processed_filepaths = flyer_analysis.process_files_as_read()
        flyer_analysis.close()
        run_stop = datetime.datetime.now()
        #shut down when that function returns
        msg = 'Flyer analysis stream processor '
        if args.output_dir is not None :
            msg+=f'writing to {args.output_dir} '
        msg+= 'shut down'
        flyer_analysis.logger.info(msg)
        msg = f'{n_read} total messages were consumed'
        if len(processed_filepaths)>0 :
            msg+=f', {n_processed} messages were successfully processed,'
            msg+=f' and the following {len(processed_filepaths)} plot file'
            msg+=' was' if len(processed_filepaths)==1 else 's were'
            msg+=' created'
        else :
            msg+=f' and {n_processed} messages were successfully processed'
        msg+=f' from {run_start} to {run_stop}'
        for fn in processed_filepaths :
            msg+=f'\n\t{fn}'
        flyer_analysis.logger.info(msg)

def main(args=None) :
    FlyerAnalysisStreamProcessor.run_from_command_line(args=args)

if __name__=='__main__' :
    main()