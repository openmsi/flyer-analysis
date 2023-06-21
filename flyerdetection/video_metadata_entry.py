# imports
from sqlalchemy import Integer, Float, String
from sqlalchemy.orm import mapped_column
from .orm_base import ORMBase


class VideoMetadataEntry(ORMBase):
    """
    A class describing entries in a table correlating individual videos
    with metadata from the FileMaker DB
    """

    VIDEO_METADATA_TABLE_NAME = "video_metadata"

    __tablename__ = VIDEO_METADATA_TABLE_NAME

    ID = mapped_column(Integer, primary_key=True)
    performed_by = mapped_column(String)               
    date = mapped_column(String)               
    energy = mapped_column(Integer)               
    theoretical_beam_diameter = mapped_column(Float)             
    fluence = mapped_column(Float)             
    beam_shaper_input_beam_diameter = mapped_column(Integer)               
    beam_shaper = mapped_column(String)               
    effective_focal_length = mapped_column(Integer)               
    drive_laser_mode = mapped_column(String)               
    oscillator_setting = mapped_column(Integer)               
    amplifier_setting = mapped_column(Integer)               
    attenuator_angle = mapped_column(Integer)               
    new_energy_measurement = mapped_column(String)               
    booster_amp_setting = mapped_column(Integer)               
    preamp_output_power = mapped_column(Integer)               
    pdv_spot_size = mapped_column(String)               
    focusing_lens_arrangement = mapped_column(String)               
    system_configuration = mapped_column(String)               
    current_set_point = mapped_column(String)               
    oscilloscope_range = mapped_column(String)               
    pdv_method = mapped_column(String)               
    seed_laser_wavelength = mapped_column(String)               
    reference_laser_wavelength = mapped_column(String)               
    time_per_div = mapped_column(String)               
    carrier_freq = mapped_column(String)               
    camera_lens = mapped_column(String)               
    doubler = mapped_column(String)               
    camera_aperture = mapped_column(String)               
    lens_aperture = mapped_column(String)               
    camera_filter = mapped_column(String)               
    illumination_laser = mapped_column(String)               
    laser_filter = mapped_column(String)               
    speed = mapped_column(String)               
    exposure = mapped_column(String)               
    high_speed_camera = mapped_column(String)               
    beam_profiler_filter = mapped_column(String)               
    beam_profiler_gain = mapped_column(String)               
    beam_profiler_exposure = mapped_column(String)               
    base_pressure = mapped_column(String)               
    pdv_spot_flyer_ratio = mapped_column(String)               
    sample_recovery_method = mapped_column(String)               
    launch_ratio = mapped_column(String)               
    launch_package_holder = mapped_column(String)               
    flyer_tilt = mapped_column(String)               
    flyer_curvature = mapped_column(String)               
    camera_filename = mapped_column(String)               
    return_signal_strength = mapped_column(String)               
    scope_filename = mapped_column(String)               
    beam_profile_filename = mapped_column(String)               
    max_velocity = mapped_column(String)               
    est_impact_velocity = mapped_column(String)               
    launch_package_orientation = mapped_column(String)               
    video_quality = mapped_column(String)               
    recovery_box = mapped_column(String)               
    recovery_row = mapped_column(String)               
    recovery_column = mapped_column(String)               
    spall_state = mapped_column(String)               
    experiment_day_counter = mapped_column(String)               
    grant_funding = mapped_column(String)               
    launch_id = mapped_column(String)               
    experiment_type = mapped_column(String)               
    notes = mapped_column(String)               
    recordid = mapped_column(String)               

    def __init__(self):
        pass
