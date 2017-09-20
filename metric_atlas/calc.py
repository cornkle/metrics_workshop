"""
This module contains all calculation functions for the climate metrics atlas

Every calc script must return a 2d cube (collapsed over time) and a 1d time series cube (collapsed over area). Based
on these two aggregations, all possible following anomaly calculations and plots can be handled.

2017
"""

import iris
import iris.coord_categorisation
import constants as cnst
import numpy as np
import numpy.ma as ma
import cf_units
from scipy import stats
import utils
import pdb


def _getSeasConstr(name):
    """
    A few definitions for seasonal slicing

    :param name: string indicating the season
    :return: corresponding iris contraint to be used for extracting a seasonal time slice
    """

    sncon = {'ann': iris.Constraint(month_number=lambda cell: 1 <= cell <= 12),
             'mj': iris.Constraint(month_number=lambda cell: 5 <= cell <= 6),
             'jj': iris.Constraint(month_number=lambda cell: 6 <= cell <= 7),
             'ja': iris.Constraint(month_number=lambda cell: 7 <= cell <= 8),
             'as': iris.Constraint(month_number=lambda cell: 8 <= cell <= 9),
             'so': iris.Constraint(month_number=lambda cell: 9 <= cell <= 10),
             'jan': iris.Constraint(month_number=lambda cell: cell == 1),
             'feb': iris.Constraint(month_number=lambda cell: cell == 2),
             'mar': iris.Constraint(month_number=lambda cell: cell == 3),
             'apr': iris.Constraint(month_number=lambda cell: cell == 4),
             'may': iris.Constraint(month_number=lambda cell: cell == 5),
             'jun': iris.Constraint(month_number=lambda cell: cell == 6),
             'jul': iris.Constraint(month_number=lambda cell: cell == 7),
             'aug': iris.Constraint(month_number=lambda cell: cell == 8),
             'sep': iris.Constraint(month_number=lambda cell: cell == 9),
             'oct': iris.Constraint(month_number=lambda cell: cell == 10),
             'nov': iris.Constraint(month_number=lambda cell: cell == 11),
             'dec': iris.Constraint(month_number=lambda cell: cell == 12),
             'djf': iris.Constraint(month_number=lambda cell: (cell == 12) | (1 <= cell <= 2)),
             'mam': iris.Constraint(month_number=lambda cell: 3 <= cell <= 5),
             'jja': iris.Constraint(month_number=lambda cell: 6 <= cell <= 8),
             'jas': iris.Constraint(month_number=lambda cell: 7 <= cell <= 9),
             'jjas': iris.Constraint(month_number=lambda cell: 6 <= cell <= 9),
             'mjjas': iris.Constraint(month_number=lambda cell: 5 <= cell <= 9),
             'son': iris.Constraint(month_number=lambda cell: 9 <= cell <= 11)
             }

    return (sncon[name])


def _subsetByTime(cube, start_int, end_int):
    time_constraint = iris.Constraint(year=lambda cell: start_int < cell <= end_int)
    subset = cube.extract(time_constraint)

    return (subset)


def annualMax(cubein, season, ncfile):
    '''
    Calculates the annual maximum of a variable.

    :param incube: single variable cube from CMIP5 raw data
    :param season: string indicating season, read by _getSeasConstr() to get season contraint
    :param ncfile: full string for output netcdf file
    :return: single model netcdf file
    '''

    print ncfile
    print 'Calculating annual maximum'
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_year(cubein, 'time', name='year')
    iris.coord_categorisation.add_month_number(cubein, 'time', name='month_number')

    slicer = _getSeasConstr(season)
    cubein = cubein.extract(slicer)

    if "pr_" in ncfile:
        cubein.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        cubein.convert_units('Celsius')

    calc = cubein.aggregated_by(['year'], iris.analysis.MAX)
    tseries = calc.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    calc2d = utils.time_slicer(calc, fdict['scenario'])
    c2d = calc2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(calc, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile)
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)


def annualMin(cubein, season, ncfile):
    '''
    Calculates the annual minimum of the variable.

    :param incube: single variable cube from CMIP5 raw data
    :param season: string indicating season, read by _getSeasConstr() to get season contraint
    :param ncfile: full string for output netcdf file
    :return: single model netcdf file
    '''

    print ncfile
    print 'Calculating annual minimum'
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_year(cubein, 'time', name='year')
    iris.coord_categorisation.add_month_number(cubein, 'time', name='month_number')

    slicer = _getSeasConstr(season)
    cubein = cubein.extract(slicer)

    if "pr_" in ncfile:
        cubein.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        cubein.convert_units('Celsius')

    calc = cubein.aggregated_by(['year'], iris.analysis.MIN)
    tseries = calc.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    calc2d = utils.time_slicer(calc, fdict['scenario'])
    c2d = calc2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(calc, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile)
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)


def annualTotalRain(incube, season, ncfile):
    '''
    Calculates the total rain over the time period

    :param incube: precipitation cube from CMIP5 raw data
    :param season: string indicating season, read by _getSeasConstr() to get season contraint
    :param ncfile: full string for output netcdf file
    :return: single model netcdf file
    '''

    print ncfile
    print 'Calculating total rain'
    fdict = utils.split_filename_path(ncfile)

    slicer = _getSeasConstr(season)
    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')

    incube = incube.extract(slicer)
    incube.convert_units('kg m-2 day-1')

    calc = incube.aggregated_by(['year'], iris.analysis.SUM)
    tseries = calc.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    calc2d = utils.time_slicer(calc, fdict['scenario'])
    c2d = calc2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(calc, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile)
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)


def _annualMeanThresh(incube, season, ncfile, lower_threshold=None):
    '''
    Calculates the annual mean over the time period

    TODO: allow lower threshold to compute mean based on e.g. RAINY days rather than all days

    :param incube: single variable cube from CMIP5 raw data
    :param season: string indicating season, read by _getSeasConstr() to get season contraint
    :param ncfile: full string for output netcdf file
    :return: single model netcdf file
    '''

    print ncfile
    print 'Calculating annual mean'
    fdict = utils.split_filename_path(ncfile)

    slicer = _getSeasConstr(season)
    iris.coord_categorisation.add_year(incube, 'time', name='year')
    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')

    incube = incube.extract(slicer)

    if "pr_" in ncfile:
        incube.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        incube.convert_units('Celsius')

    csum = incube.aggregated_by(['year'], iris.analysis.SUM)
    ccount = incube.aggregated_by(['year'], iris.analysis.COUNT, function=lambda values: values >= lower_threshold)
    calc = csum/ccount # mean
    tseries = calc.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    calc2d = utils.time_slicer(calc, fdict['scenario'])
    c2d = calc2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(calc, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile) # yearly time series
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)


def monthlyClimatologicalMean(incube, season, ncfile):
    '''
    Calculates the climatological monthly means over the time period

    TODO: allow lower threshold to compute mean based on e.g. RAINY days rather than all days

    :param incube: single variable cube from CMIP5 raw data
    :param season: string indicating season, read by _getSeasConstr() to get season constraint
    :param ncfile: full string for output netcdf file
    :return: single model netcdf file
    '''

    print ncfile
    print 'Calculating climatological monthly mean'
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')

    #    slicer = _getSeasConstr(season)
    #    cubein = incube.extract(slicer)


    if "pr_" in ncfile:
        incube.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        incube.convert_units('Celsius')

    calc = incube.aggregated_by('month_number', iris.analysis.MEAN)
    tseries = calc.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    calc2d = utils.time_slicer(calc, fdict['scenario'])
    c2d = calc2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(calc, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile) # monthly time series, 12 entries
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)


def _annualnbDayPerc(incube, season, ncfile, upper_threshold=None, lower_threshold=None):
    '''
    Calculate percentage of days per year with higher value than threshold.
    Choose thresholds as needed e.g. 30mm for extreme and 1mm for rainy day.

    :param incube: precipitation cube from CMIP5 raw data
    :param season: string indicating season, read by _getSeasConstr() to get season contraint
    :param ncfile: full string for output netcdf file
    :param upper_threshold: threshold (>=) defining the value to be exceeded (e.g. extreme value or rainy day value
    :param lower_threshold: threshold (>=) defining the minimum value of valid pixels (eg. 0 or 0.1 or 1)
    :return: single model netcdf file
    '''
    if not upper_threshold:
        print "No threshold given, please provide upper threshold, stopping calculation"
        return

    print ncfile
    print "Calculating percentage of days with variable above " + str(upper_threshold)
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')

    slicer = _getSeasConstr(season)
    incube = incube.extract(slicer)
    incube.coord('latitude').guess_bounds()
    incube.coord('longitude').guess_bounds()
    if "pr_" in ncfile:
        incube.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        incube.convert_units('Celsius')

    bigger = incube.aggregated_by('year', iris.analysis.COUNT, function=lambda values: values >= upper_threshold)
    monthcount = incube.aggregated_by('year', iris.analysis.COUNT, function=lambda values: values >= lower_threshold)
    bigger.data = bigger.data.astype(float)
    monthcount.data = monthcount.data.astype(float)

    bigger_tseries = bigger.collapsed(['longitude', 'latitude'], iris.analysis.SUM)

    bigger2d = utils.time_slicer(bigger, fdict['scenario'])
    bigger_c2d = bigger2d.collapsed('year', iris.analysis.SUM)

    monthcount_tseries = monthcount.collapsed(['longitude', 'latitude'], iris.analysis.SUM)

    monthcount2d = utils.time_slicer(monthcount, fdict['scenario'])
    monthcount_c2d = monthcount2d.collapsed('year', iris.analysis.SUM)

    tseries = (bigger_tseries / monthcount_tseries) * 100
    c2d = (bigger_c2d / monthcount_c2d) * 100

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    iris.save(tseries, ncfile)
    iris.save(c2d, nc2d)


def _annualnbDay(incube, season, ncfile, threshold=None):
    '''
    Calculate number of days per year with higher value than threshold.
    Choose threshold as needed e.g. 30mm for extreme and 1mm for rainy day.

    :param incube: precipitation cube from CMIP5 raw data
    :param season: string indicating season, read by _getSeasConstr() to get season contraint
    :param ncfile: full string for output netcdf file
    :return: single model netcdf file
    '''
    if not threshold:
        print 'No threshold given, stopping calculation'
        return

    print ncfile
    print "Calculating number of days with variable above " + str(threshold)
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')

    slicer = _getSeasConstr(season)
    incube = incube.extract(slicer)
    incube.coord('latitude').guess_bounds()
    incube.coord('longitude').guess_bounds()
    if "pr_" in ncfile:
        incube.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        incube.convert_units('Celsius')

    bigger = incube.aggregated_by('year', iris.analysis.COUNT, function=lambda values: values >= threshold)
    bigger.units = incube.units
    bigger.data = bigger.data.astype(float)

    tseries = bigger.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    bigger2d = utils.time_slicer(bigger, fdict['scenario'])
    c2d = bigger2d.collapsed('year', iris.analysis.MEDIAN)

    trend2d = trend(bigger, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile)
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)

def _xDaySum_AnnualMax(incube, season, ncfile, nb_days=None):

    if not nb_days:
        print 'Number of days for aggregation not given, stopping calculation'
        return

    print ncfile
    print "Aggregating variable for " + str(nb_days) + "-day moving windows."
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')

    slicer = _getSeasConstr(season)
    incube = incube.extract(slicer)

    if "pr_" in ncfile:
        incube.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        print('This aggregation makes no sense for temperature. Stopping calculation')
        return

    calc = incube.rolling_window('time', iris.analysis.SUM, nb_days)
    calc = calc.aggregated_by(['year'], iris.analysis.MAX)

    tseries = calc.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    calc2d = utils.time_slicer(calc, fdict['scenario'])
    c2d = calc2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(calc, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile)  # monthly time series, 12 entries
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)


def _xDayMean_AnnualMax(incube, season, ncfile, nb_days=None):

    if not nb_days:
        print 'Number of days for aggregation not given, stopping calculation'
        return

    print ncfile
    print "Aggregating variable for " + str(nb_days) + "-day moving windows."
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')

    slicer = _getSeasConstr(season)
    incube = incube.extract(slicer)

    cube2plot = incube

    if "pr_" in ncfile:
        cube2plot.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        print('This aggregation makes no sense for temperature. Stopping calculation')
        return

    calc = cube2plot.rolling_window('time', iris.analysis.MEAN, nb_days)
    calc = calc.aggregated_by(['year'], iris.analysis.MAX)
    tseries = calc.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    calc2d = utils.time_slicer(calc, fdict['scenario'])
    c2d = calc2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(calc, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile)  # monthly time series, 12 entries
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)


def annualRainyDaysPerc(incube, season, ncfile):
    _annualnbDayPerc(incube, season, ncfile, upper_threshold=cnst.RAINYDAY_THRESHOLD, lower_threshold=0)


def annualExtremeRain30Perc(incube, season, ncfile):
    _annualnbDayPerc(incube, season, ncfile, upper_threshold=30, lower_threshold=cnst.RAINYDAY_THRESHOLD)


def annualExtremeRain50Perc(incube, season, ncfile):
    _annualnbDayPerc(incube, season, ncfile, upper_threshold=50, lower_threshold=cnst.RAINYDAY_THRESHOLD)


def annualExtremeRain100Perc(incube, season, ncfile):
    _annualnbDayPerc(incube, season, ncfile, upper_threshold=100, lower_threshold=cnst.RAINYDAY_THRESHOLD)


def annualHotDaysPerc(incube, season, ncfile):
    _annualnbDayPerc(incube, season, ncfile, upper_threshold=cnst.HOTDAYS_THRESHOLD, lower_threshold=-50)


def annualRainyDays(incube, season, ncfile):
    _annualnbDay(incube, season, ncfile, threshold=cnst.RAINYDAY_THRESHOLD)


def annualExtremeRain30(incube, season, ncfile):
    _annualnbDay(incube, season, ncfile, threshold=30)


def annualExtremeRain50(incube, season, ncfile):
    _annualnbDay(incube, season, ncfile, threshold=50)


def annualExtremeRain100(incube, season, ncfile):
    _annualnbDay(incube, season, ncfile, threshold=100)


def annualHotDays(incube, season, ncfile):
    _annualnbDay(incube, season, ncfile, threshold=cnst.HOTDAYS_THRESHOLD)

def annualWindDays(incube, season, ncfile):
    _annualnbDay(incube, season, ncfile, threshold=cnst.STRONGWIND_THRESHOLD)

def annualMaxRain_5dSum(incube,season,ncfile):
    _xDaySum_AnnualMax(incube,season,ncfile, nb_days=5)

def annualMaxRain_3dSum(incube,season,ncfile):
    _xDaySum_AnnualMax(incube,season,ncfile, nb_days=3)

def annualMaxRain_2dSum(incube,season,ncfile):
    _xDaySum_AnnualMax(incube,season,ncfile, nb_days=2)

def annualMax_5dMean(incube,season,ncfile):
    _xDaySum_AnnualMax(incube,season,ncfile, nb_days=5)

def AnnualMax_3dMean(incube,season,ncfile):
    _xDaySum_AnnualMax(incube,season,ncfile, nb_days=3)

def annualMax_2dMean(incube,season,ncfile):
    _xDaySum_AnnualMax(incube,season,ncfile, nb_days=2)

def annualMean(incube,season,ncfile):
    _annualMeanThresh(incube, season, ncfile, lower_threshold=-999)

def annualMeanRainyDay(incube,season,ncfile):
    _annualMeanThresh(incube, season, ncfile, lower_threshold=cnst.RAINYDAY_THRESHOLD)

def SPIxMonthly(incube, season, ncfile):
    """
    Calculate SPI for given period up to one year.
    The SPI is the anomaly with respect to the chosen scenario baseline period.
    period - climatological_mean / climatological_std

    :param incube: precipitation cube from CMIP5 raw data
    :param season: string indicating season, read by _getSeasConstr() to get season contraint
    :param ncfile: full string for output netcdf file
    :return: single model netcdf file
    """

    print 'Calculating SPI for ' + str(season)
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')
    slicer = _getSeasConstr(season)

    incube = incube.extract(slicer)


    c_monthly = incube.aggregated_by(['year'], iris.analysis.MEAN)
    c_monthly.convert_units('kg m-2 day-1')

    # This is the monthly climatology (mean and std deviation)
    std = c_monthly.collapsed('year', iris.analysis.STD_DEV)
    mean = c_monthly.collapsed('year', iris.analysis.MEAN)

    # We need to change the shape of the monthly climatologies to match the shape of the timeseries (in the cube c_monthly)
    mean = mean.data
    std = std.data

    clim_mean_data = np.repeat(mean.reshape(1, mean.shape[0], mean.shape[1]), c_monthly.shape[0],
                               axis=0)  # np.tile(mean.data, (c_monthly.shape[0] / mean.shape[0], 1, 1))
    clim_std_data = np.repeat(std.reshape(1, std.shape[0], std.shape[1]), c_monthly.shape[0],
                              axis=0)  # np.tile(std.data, (c_monthly.shape[0] / std.shape[0], 1, 1))

    clim_mean_cube = c_monthly.copy(clim_mean_data)
    clim_std_cube = c_monthly.copy(clim_std_data)

    spi = (c_monthly - clim_mean_cube) / clim_std_cube

    pdb.set_trace()

    iris.save(spi, ncfile)  #SPI is 3d cube at the moment. Not sure what we want to plot!


# def SPIbiannual(incube, season, ncfile):
#     """
#     Calculate SPI for given period up to one year.
#     The SPI is the anomaly with respect to the chosen scenario baseline period.
#     period - climatological_mean / climatological_std
#
#     :param incube: precipitation cube from CMIP5 raw data
#     :param season: string indicating season, read by _getSeasConstr() to get season contraint
#     :param ncfile: full string for output netcdf file
#     :return: single model netcdf file
#     """
#
#     print 'Calculating SPI for ' + str(season)
#
#     iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
#     iris.coord_categorisation.add_year(incube, 'time', name='year')
#     slicer = _getSeasConstr(season)
#
#     incube = incube.extract(slicer)
#
#     c_monthly = incube.aggregated_by(['year'], iris.analysis.MEAN)
#     c_monthly.convert_units('kg m-2 day-1')
#
#     # This is the monthly climatology (mean and std deviation)
#     std = c_monthly.collapsed('year', iris.analysis.STD_DEV)
#     mean = c_monthly.collapsed('year', iris.analysis.MEAN)
#
#     # We need to change the shape of the monthly climatologies to match the shape of the timeseries (in the cube c_monthly)
#     mean = mean.data
#     std = std.data
#
#     clim_mean_data = np.repeat(mean.reshape(1, mean.shape[0], mean.shape[1]), c_monthly.shape[0],
#                                axis=0)  # np.tile(mean.data, (c_monthly.shape[0] / mean.shape[0], 1, 1))
#     clim_std_data = np.repeat(std.reshape(1, std.shape[0], std.shape[1]), c_monthly.shape[0],
#                               axis=0)  # np.tile(std.data, (c_monthly.shape[0] / std.shape[0], 1, 1))
#
#     clim_mean_cube = c_monthly.copy(clim_mean_data)
#     clim_std_cube = c_monthly.copy(clim_std_data)
#
#     spi = (c_monthly - clim_mean_cube) / clim_std_cube
#
#     iris.save(spi, ncfile)



def onsetMarteau(incube, season, ncfile):
    """
    Calculate Marteau monsoon onset. Season is fixed to onset period

    :param incube: precipitation cube from CMIP5 raw data
    :param ncfile: full string for output netcdf file
    :return: single model netcdf file
    """

    season = 'mjjas'
    fdict = utils.split_filename_path(ncfile)

    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')
    iris.coord_categorisation.add_day_of_year(incube, 'time', name='day_of_year')
    slicer = _getSeasConstr(season)
    cubein = incube.extract(slicer)

    cube2plot = cubein
    cube2plot.convert_units('kg m-2 day-1')
    yrs = cube2plot.aggregated_by('year', iris.analysis.MEAN)

    empty = yrs.data
    years = yrs.coord('year').points
    dates = []
    tester = 14
    onsets = np.zeros((empty.shape[0], empty.shape[1], empty.shape[2]), float)

    for yr in years:
        yrslice = iris.Constraint(year=lambda cell: cell == yr)
        holdr = cubein.extract(yrslice)
        strt_date = holdr.coord('day_of_year').points[0]
        holdr = holdr.data
        for x in range(0, holdr.shape[2]):
            for y in range(0, holdr.shape[1]):
                latmean = 0
                cnt0 = 0
                A = 0
                B = 0
                C = 0
                for t in xrange(0, holdr.shape[0] - tester - 6):
                    if holdr[t, y, x] > 1.0:
                        A4 = 1
                    else:
                        A4 = 0
                    if holdr[t + 1, y, x] + holdr[t, y, x] > 20.0:
                        A1 = 1
                    else:
                        A1 = 0
                    A2 = 1
                    t2 = 2
                    while t2 < tester - 6:
                        drytest = holdr[t + t2, y, x] + holdr[t + t2 + 1, y, x] + holdr[t + t2 + 2, y, x] + holdr[
                            t + t2 + 3, y, x] + holdr[t + t2 + 4, y, x] + holdr[t + t2 + 5, y, x] + holdr[
                                      t + t2 + 6, y, x]
                        if drytest < 5.0:
                            A2 = 0
                            break
                        else:
                            t2 = t2 + 1
                    A3 = A4 + A2 + A1
                    if A3 == 3:
                        latmean = t + strt_date

                        onsets[yr - years[0], y, x] = latmean

                        break
                    else:
                        continue
                    break
                if latmean == 0:
                    onsets[yr - years[0], y, x] = float('NaN')

    yrs.data = onsets[:]

    tseries = yrs.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    yrs2d = utils.time_slicer(yrs, fdict['scenario'])
    c2d = yrs2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(yrs, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile)
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)


def _countSpells(incube, season, ncfile, spell_length=None, lower_threshold=None, upper_threshold=None):
    '''
    Calculates the number of periods of a spell of length 'spell length' above or equal
    'lower threshold' or below 'upper threshold'.
    '''
    def count_func(data, threshold, axis, spell_length):
        #print(data.shape)
        print(axis)
        if axis < 0:
            # just cope with negative axis numbers
            axis += data.ndim
        #print(axis)
        # Threshold the data to find the 'significant' points.
        if lower_threshold:
            data_hits = data >= threshold

        if upper_threshold:
            data_hits = data < threshold

        # Make an array with data values "windowed" along the time axis.
        hit_windows = iris.util.rolling_window(data_hits, window=spell_length, axis=axis) # rolling window along time axis

        # Find the windows "full of True-s" (along the added 'window axis').
        full_windows = np.all(hit_windows, axis=axis+1)
        # Count points fulfilling the condition (along the time axis).
        spell_point_counts = np.sum(full_windows, axis=axis, dtype=int)
        return spell_point_counts

    if not spell_length:
        print "No spell length given, please provide. Stopping calculation"
        return

    if (upper_threshold and lower_threshold):
        print "Upper and lower threshold given. Please provide exactly one (upper or lower) threshold. Stopping calculation"
        return

    if not (upper_threshold or lower_threshold):
        print "No threshold given. Please provide one (upper or lower) threshold. Stopping calculation"
        return

    fdict = utils.split_filename_path(ncfile)

    if upper_threshold:
        threshold = upper_threshold
    else:
        threshold = lower_threshold

    print ncfile
    print "Calculating number of spells equal or longer than " + str(spell_length) +' days.'

    iris.coord_categorisation.add_month_number(incube, 'time', name='month_number')
    iris.coord_categorisation.add_year(incube, 'time', name='year')

    slicer = _getSeasConstr(season)
    incube = incube.extract(slicer)
    incube.coord('latitude').guess_bounds()
    incube.coord('longitude').guess_bounds()
    if "pr_" in ncfile:
        incube.convert_units('kg m-2 day-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        incube.convert_units('Celsius')

    #Start spell calculation
    # Make an aggregator from days count
    SPELL_COUNT = iris.analysis.Aggregator('spell_count', count_func,
                                     units_func=lambda units: 1)
    # Calculate the statistic
    calc = incube.aggregated_by(['year'], SPELL_COUNT, threshold=threshold,
                                spell_length=spell_length)
    calc.units = incube.units
    tseries = calc.collapsed(['longitude', 'latitude'], iris.analysis.MEDIAN)

    calc2d = utils.time_slicer(calc, fdict['scenario'])
    c2d = calc2d.collapsed('year', iris.analysis.MEDIAN)
    trend2d = trend(calc, season, ncfile)

    nc2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[1])
    nctrend2d = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])

    iris.save(tseries, ncfile)  # monthly time series, 12 entries
    iris.save(c2d, nc2d)
    iris.save(trend2d, nctrend2d)

def wetSpell10(incube, season, ncfile):
    _countSpells(incube, season, ncfile, spell_length=10, lower_threshold=cnst.RAINYDAY_THRESHOLD)

def drySpell6(incube, season, ncfile):
    _countSpells(incube, season, ncfile, spell_length=6, upper_threshold=cnst.RAINYDAY_THRESHOLD)


def trend(cubein, season, ncfile):
    '''
    Calculates the annual trend either for 1950-2000 or for 2010-2060
    Can calculate the trend for one period, or (if 'month_number' is a coordinate name), it will calculate the trend for each month
    
    :param incube: timeseries of a metric either for 1 period (e.g. JAS), or for all months of the year
    :param season: season name as recognised by the function _getSeasConstr
    :param ncfile: full string for output netcdf file
    returns: trend for a single model netcdf 

    TODO: Review code & check that behaviour for multiple months is as expected
    '''
    if 'month_number' not in [coord.name() for coord in cubein.coords()]:
        iris.coord_categorisation.add_month_number(cubein, 'time', name='month_number')
    if 'year' not in [coord.name() for coord in cubein.coords()]:
        iris.coord_categorisation.add_year(cubein, 'time', name='year')

    if "historical_" in ncfile:
        incube = _subsetByTime(cubein, cnst.HIST[0], cnst.HIST[1])
    else:
        incube = _subsetByTime(cubein, cnst.FUT_TREND[0], cnst.FUT_TREND[1])

    # Assume unknown units only exist for precip (NB: Units are kg/m2/s)
    if incube.units == 'unknown':
        incube.units = cf_units.Unit('kg m-2 s-1')

    # Make sure there aren't any invalid grid cells in the data
    incube.data = ma.masked_invalid(incube.data)

    # Are we quantifying the trend for each month of the year ('ann') or just for one period (e.g. JAS)?
    if "pr_" in ncfile:
        incube_y = incube.aggregated_by(['year'], iris.analysis.SUM)
        incube_y.convert_units('kg m-2 month-1')

    if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
        incube_y = incube.aggregated_by(['year'], iris.analysis.MEAN)
        incube_y.convert_units('Celsius')

    month_numbers = np.unique(incube_y.coord('month_number').points)

    if len(month_numbers) > 1:

        if "pr_" in ncfile:
            incube_ym = incube.aggregated_by(['year', 'month_number'], iris.analysis.SUM)
            incube_ym.convert_units('kg m-2 month-1')

        if ("tas_" in ncfile) or ('tasmax_' in ncfile) or ('tasmin_' in ncfile):
            incube_ym = incube.aggregated_by(['year', 'month_number'], iris.analysis.MEAN)
            incube_ym.convert_units('Celsius')

        slopedata1mon = np.zeros(incube_ym[0].shape).reshape((1, incube_ym[0].shape[0], incube_ym[0].shape[1]))
        slopedata = np.repeat(slopedata1mon, 12, axis=0)
        moncoord = iris.coords.DimCoord(points=np.arange(1, 13), long_name='month_number', units='1')
        slope = iris.cube.Cube(slopedata, long_name='Trend', units=incube_ym.units,
                               dim_coords_and_dims=[(moncoord, 0), (incube.coord('latitude'), 1),
                                                    (incube.coord('longitude'), 2)])
        for mon in month_numbers:
            # print mon
            slicer = iris.Constraint(month_number=lambda cell: cell == mon)
            incube1mon = incube_ym.extract(slicer)
            for x in np.arange(len(incube.coord('longitude').points)):
                for y in np.arange(len(incube.coord('latitude').points)):
                    if np.all(incube1mon.data[:, y, x].mask):
                        slope.data[mon - 1, y, x] = ma.masked
                    else:
                        # Outputs: slope, intercept, r-value, pvalue, std_err 
                        # for py34: reg.slope                        
                        reg = stats.linregress(np.arange(incube1mon.shape[0]), incube1mon.data[:, y, x])
                        slope.data[mon - 1, y, x] = reg[0]

    else:
        # No need to loop through months in this case
        slopedata = np.zeros(incube_y[0].shape)
        slope = iris.cube.Cube(slopedata, long_name='Trend', units=incube_y.units,
                               dim_coords_and_dims=[(incube.coord('latitude'), 0), (incube.coord('longitude'), 1)])
        for x in np.arange(len(incube.coord('longitude').points)):
            for y in np.arange(len(incube.coord('latitude').points)):
                if np.all(incube_y.data[:, y, x].mask):
                    slope.data[y, x] = ma.masked
                else:
                    # Outputs: slope, intercept, r-value, pvalue, std_err 
                    # for py34: reg.slope
                    reg = stats.linregress(np.arange(incube_y.shape[0]), incube_y.data[:, y, x])
                    slope.data[y, x] = reg[0]

    return (slope)

#    ncfile_trend = ncfile.replace(cnst.AGGREGATION[0], cnst.AGGREGATION[2])
#    iris.save(slope, ncfile)
