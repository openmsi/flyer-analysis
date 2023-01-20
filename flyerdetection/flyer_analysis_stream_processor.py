#imports
from openmsistream import DataFileStreamProcessor

class FlyerAnalysisStreamProcessor(DataFileStreamProcessor) :
    """
    A class to run flyer analysis for all .bmp images in a topic and add their results to an ouput file
    """

    @classmethod
    def run_from_command_line(cls,args=None) :
        """
        Run the stream-processed analysis code from the command line
        """
        #make the argument parser
        parser = cls.get_argument_parser()
        args = parser.parse_args(args=args)
        #make the stream processor
        #plot_maker = cls(args.output_dir,args.pdv_plot_type,args.config,args.topic_name,
        #                 n_threads=args.n_threads,
        #                 update_secs=args.update_seconds,
        #                 consumer_group_ID=args.consumer_group_ID,
        #                 logger_file=args.output_dir)
        ##start the plot maker running (returns total number of messages read and names of plot files created)
        #run_start = datetime.datetime.now()
        #msg = f'Listening to the {args.topic_name} topic to find Lecroy data files and create '
        #msg+= f'{args.pdv_plot_type} plots'
        #plot_maker.logger.info(msg)
        #n_read,n_processed,plot_filepaths = plot_maker.make_plots_as_available()
        #plot_maker.close()
        #run_stop = datetime.datetime.now()
        ##shut down when that function returns
        #msg = 'PDV plot maker '
        #if args.output_dir is not None :
        #    msg+=f'writing to {args.output_dir} '
        #msg+= 'shut down'
        #plot_maker.logger.info(msg)
        #msg = f'{n_read} total messages were consumed'
        #if len(plot_filepaths)>0 :
        #    msg+=f', {n_processed} messages were successfully processed,'
        #    msg+=f' and the following {len(plot_filepaths)} plot file'
        #    msg+=' was' if len(plot_filepaths)==1 else 's were'
        #    msg+=' created'
        #else :
        #    msg+=f' and {n_processed} messages were successfully processed'
        #msg+=f' from {run_start} to {run_stop}'
        #for fn in plot_filepaths :
        #    msg+=f'\n\t{fn}'
        #plot_maker.logger.info(msg)

def main(args=None) :
    FlyerAnalysisStreamProcessor.run_from_command_line(args=args)

if __name__=='__main__' :
    main()