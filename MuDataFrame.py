# -*- coding: utf-8 -*-
"""
=============================================
Program : CrateAnalysis/MuonDataFrame.py
=============================================
Summary:
"""
__author__ = "Sadman Ahmed Shanto"
__date__ = "2021-02-17"
__email__ = "sadman-ahmed.shanto@ttu.edu"

# import feather
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
import os
import matplotlib as mpl
import itertools
import datetime
import qgrid
from matplotlib.backends.backend_pdf import PdfPages
from collections import Counter
from collections import OrderedDict
from collections import defaultdict
from multiprocessing import Pool
from pandas_profiling import ProfileReport
from Histo2d import Histo2D
#from muondataframegui import show
from PIL import Image
from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from multipledispatch import dispatch
from Notify import Notify
from datetime import timedelta
from MuonDataFrame import *
import copy


def getCombinedMDFO(runStart, runEnd):
    """
    Inputs: runStart->int,runEnd->int
    Output: MuDataFrame Object
    Process: it combines the runfiles defined in the input from runStart to runEnd and
             returns a comprehensive MuDataFrame Object with all the run information
    """
    r1, r2 = runStart, runEnd
    lead_files = [
        "processed_data/run{}.csv".format(i) for i in range(r1, r2 + 1)
    ]

    self_c = []  #collection of objects

    for file in lead_files:
        self_c.append(MuDataFrame(file))  #Muon Data Frame Object for Lead

    mdf_list = [i.events_df for i in self_c]
    mdf_lead = self_c[0].getMergedMDF(mdf_list)

    self_lead = copy.copy(self_c[0])
    self_lead.events_df = mdf_lead

    self_lead.longDataMode()

    mdf_lead = self_lead.events_df
    self_lead.og_df = mdf_lead.copy()
    return self_lead


def getEmissionOutputCSV(df, fileName):
    """
    Inputs: df-dataframe,fileName-string
    Output: NA
    Process: it resets the index of df and accesses a csv file
    """
    
    df.events_df.reset_index(drop=True, inplace=True)
    df.events_df.to_csv(fileName)


np.warnings.filterwarnings('ignore')


def getPhysicalUnits(asym):
    """
    Inputs: asym-float
    Output: float
    Process: it just multiplies asym by 55/.6
    """    
    return (55 / 0.6) * asym


def getXatZPlane(x1, x2, zplane, dsep):
    """
    Inputs: x1,x2-array, zplane,dsep-int
    Output: float
    Process: it uses the given data to project x onto the plane of interest
    """    
    x = (zplane / dsep) * (getPhysicalUnits(x1) -
                           getPhysicalUnits(x2)) + getPhysicalUnits(x1)
    return x


# CODE FOR COUNTING
def append_pdf(input, output):
    """
    Inputs: input,output-file
    Output: NA
    Process: it adds the input to the output, page by page
    """    
    [
        output.addPage(input.getPage(page_num))
        for page_num in range(input.numPages)
    ]


def parallelize_dataframe(df, func, path, n_cores=2):
    """
    Inputs: df,func-dataframe,path=string,n_cores=2 
    Output: dataframe
    Process: it splits the workload of analyzing the dataframe in two processes
    """    
    df_split = np.array_split(df, n_cores)
    pool = Pool(n_cores)
    df = pd.concat(pool.map(func, df_split))
    pool.close()
    pool.join()
    # df.to_hdf(path, key=path, format="table")
    df.to_hdf(path, key=path)
    # feather.write_dataframe(df, path)
    return df


def getAsymmetryUnits(phys):
    """
    Inputs: phys-float
    Output: float
    Process: it just multiplies phys by .6/.55
    """    
    return (0.6 / 0.55) * phys


def remove_if_first_index(l):
    """
    Inputs: l-dataframe
    Output: dataframe
    Process: it removes items in a dataframe if they are part of the first index
    """
    return [
        item for index, item in enumerate(l)
        if item[0] not in [value[0] for value in l[0:index]]
    ]


def conditionParser_multiple(df, conditions):
    """
    Inputs: df-dataframe,conditions-string
    Output: dataframe
    Process: it takes a series of conditions (=,<,>,<=,>=,!=) and applies them to df
    """    
    qt, op, val = conditions.split(" ")
    if op == "==":
        df = df[df[qt] == float(val)]
        print(df[df[qt] == float(val)])
    elif op == ">":
        df = df[df[qt] > float(val)]
        # print(df[df[qt] > float(val)])
    elif op == "<":
        df = df[df[qt] < float(val)]
        print(df[df[qt] < float(val)])
    elif op == ">=":
        df = df[df[qt] >= float(val)]
        print(df[df[qt] >= float(val)])
    elif op == "<=":
        df = df[df[qt] <= float(val)]
        print(df[df[qt] <= float(val)])
    elif op == "!=":
        df = df[df[qt] != float(val)]
        print(df[df[qt] != float(val)])
    return df


def conditionParser_single(df, conditions):
    """
    Inputs: df-dataframe,conditions-string
    Output: dataframe
    Process: it takes a series of conditions (=,<,>,<=,>=,!=) and applies them to df it also tests a block for errors
    """    
    qt, op, val = conditions[0].split(" ")
    if op == "==":
        try:
            df = df[df[qt] == float(val)]
            print(df[df[qt] == float(val)])
        except:
            df = df[df[qt] == val]
            print(df[df[qt] == val])
    elif op == ">":
        df = df[df[qt] > float(val)]
        # print(df[df[qt] > float(val)])
    elif op == "<":
        df = df[df[qt] < float(val)]
        print(df[df[qt] < float(val)])
    elif op == ">=":
        df = df[df[qt] >= float(val)]
        print(df[df[qt] >= float(val)])
    elif op == "<=":
        df = df[df[qt] <= float(val)]
        print(df[df[qt] <= float(val)])
    elif op == "!=":
        df = df[df[qt] != float(val)]
        print(df[df[qt] != float(val)])
    return df


def getFilteredEvents(self, df, conditions):
    """
    Inputs: df-dataframe,conditions-string
    Output: dataframe
    Process: it takes a series of conditions (=,<,>,<=,>=,!=) and applies them to df it also tests a block for errors
    """
    numConditions = len(conditions)
    if numConditions == 1:
        qt, op, val = conditions[0].split(" ")
        if op == "==":
            print(df[df[qt] == float(val)])
        elif op == ">":
            print(df[df[qt] > float(val)])
        elif op == "<":
            print(df[df[qt] < float(val)])
        elif op == ">=":
            print(df[df[qt] >= float(val)])
        elif op == "<=":
            print(df[df[qt] <= float(val)])
        elif op == "!=":
            print(df[df[qt] != float(val)])


def scrubbedDataFrame(df, queryName, numStd):
    """
    Inputs: df-dataframe, queryName-string, numStd-float
    Output: dataframe
    Process: filters the dataframe by removing elements that are more than one standard deviation away
    """
    s = df[queryName]
    s_mean = s.mean()
    s_std = s.std()
    v_low = s.mean() - numStd * s_std
    v_hi = s.mean() + numStd * s_std
    df_filtered = df[(df[queryName] < v_hi) & (df[queryName] > v_low)]
    return df_filtered


def getHistogram(df, queryName, title="", nbins=200):
    """
    Inputs: df-dataframe, queryName-string
    Output: NA
    Process: creates a histogram plot of df
    """    
    s = df[queryName]
    ax = s.plot.hist(alpha=0.7, bins=nbins, histtype='step')
    mean, std, count = s.describe().values[1], s.describe(
    ).values[2], s.describe().values[0]
    textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}".format(mean, std, count)
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.7)
    ax.text(0.80,
            0.95,
            textstr,
            transform=ax.transAxes,
            fontsize=12,
            verticalalignment='top',
            bbox=props)
    ax.set_title("Histogram of {} {}".format(queryName, title))
    plt.show()


def getFilteredHistogram(df, queryName, filter, nbins=200, title=""):
    """
    Inputs: df-dataframe, queryName-string
    Output: NA
    Process: creates a histogram plot of df
    """
    df.hist(column=queryName, bins=nbins, by=filter, histtype='step')
    plt.suptitle("Histograms of {} grouped by {} {}".format(
        queryName, filter, title))
    plt.ylabel("Frequency")
    plt.show()


class MuDataFrame:
    def __init__(self, path):
        """
        Initialize the MuonDataFrame

        :param path [string]: path to the data file
        :param d1 [string]: type of decision to be made on multiTDC events (acceptable terms are "last", "first", "min", and "max")
                            default value = last
        """
        self.events_df = pd.read_csv(path)
        self.newFileName = path.split(".")[0].split("/")[0] + "/" + path.split(
            ".")[0].split("/")[1] + ".csv"
        self.nbins = 150
        self.d_phys = 1.65  #distance between two trays in meters
        self.d_lead = 0.42  #distance (m) between top tray and lead brick
        self.d_asym = getAsymmetryUnits(self.d_phys)
        self.quant_query_terms = []
        self.default_query_terms = [
            'event_num', 'event_time', 'deadtime', 'ADC', 'TDC', 'SCh0',
            'SCh1', 'SCh2', 'SCh3', 'SCh4', 'SCh5', 'SCh6', 'SCh7', 'SCh8',
            'SCh9', 'SCh9', 'SCh11', 'l1hit', 'l2hit', 'l3hit', 'l4hit',
            'r1hit', 'r2hit', 'r3hit', 'r4hit'
        ]
        self.query_terms = self.default_query_terms + self.quant_query_terms
        self.pdfName = path.split(".")[0].split("/")[1] + ".pdf"
        self.pdfList = []
        self.runNum = self.pdfName.split(".")[0].split("_")[-1]
        self.imagelist = []
        self.og_df = self.events_df
        self.total = len(self.og_df.index)

    def longDataMode(self, zplane=42, dsep=165):
    """
    Inputs:
    Output: NA
    Process: it initializes some commands
    """
        self.getProjectionData(zplane, dsep)
        self.getProjectionData_diff(zplane, dsep)
        self.getFixedEventNums()
        self.classifyDateTime()
        self.getSerializedTimes()

    def classifyDateTime(self):
    """
    Inputs: 
    Output: 
    Process: it standardizes the hour and minute and defines whether it is day or night
    """
        timestamps = self.get("event_time")
        label = []
        for timestamp in timestamps:
            time = datetime.datetime.strptime(timestamp,
                                              "%Y-%m-%d %H:%M:%S.%f")
            hr, mi = (time.hour, time.minute)
            if (hr >= 7 and hr < 18):
                label.append("day")
            else:
                label.append("night")
        self.events_df["time_of_day"] = label

    def getProjectionData_diff(self, zplane=42, dsep=165):
    """
    Inputs:
    Output:
    Process: it creates arrays xx1 and yy1 that are projections on the plane of interest
    """
        xx_lead = getXatZPlane_diffTDC(self.get("diffL1"), self.get("diffL3"),
                                       zplane, dsep)
        yy_lead = getXatZPlane_diffTDC(self.get("diffL2"), self.get("diffL4"),
                                       zplane, dsep)

        self.events_df["xx1"] = xx_lead
        self.events_df["yy1"] = yy_lead

    def getProjectionData(self, zplane=42, dsep=165):
    """
    Inputs:
    Output:
    Process: it creates arrays xx and yy that are projections on the plane of interest
    """
        xx_lead = getXatZPlane(self.get("asymL1"), self.get("asymL3"), zplane,
                               dsep)
        yy_lead = getXatZPlane(self.get("asymL2"), self.get("asymL4"), zplane,
                               dsep)

        self.events_df["xx"] = xx_lead
        self.events_df["yy"] = yy_lead

    def getFixedEventNums(self):
    """
    Inputs:
    Output:
    Process: it creates an array which contains the event numbers
    """
        num_lead_events = len(self.events_df.index)
        lead_events_seq = [i for i in range(num_lead_events)]
        self.events_df["event_num"] = lead_events_seq

    def getSerializedTimes(self):
    """
    Inputs:
    Output:
    Process: it creates an array which contains the timestamps of the events
    """
        times_lead = np.array([
            datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
            for date in self.events_df["event_time"].values
        ])
        times_l1 = [0]
        for i in range(1, len(times_lead)):
            del_t = times_lead[i] - times_lead[i - 1]
            times_l1.append(del_t.microseconds + times_l1[i - 1])
        self.events_df["time"] = times_l1

    def addRunNumColumn(self, df):
    """
    Inputs: df-dataframe
    Output: dataframe
    Process: it adds runNum to the dataframe
    """
        df["Run_Num"] = int(self.runNum)
        return df

    def addInfoColumn(self, df, term, term2):
    """
    Inputs: term,term2-string
    Output: dataframe
    Process: it adds term to the dataframe
    """
        df[term2] = self.events_df[term]
        return df

    def getMergedMDF(self, df_list):
    """
    Inputs: df_list-array
    Output: dataframe
    Process: it concatenates the dataset and resets the index
    """
        df = pd.concat(df_list).reset_index()
        return df

    def getJnbDf(self, df):
    """
    Inputs: df-dataframe
    Output: QGrid Widget instance
    Process: it creates a QGrid Widget instance. the documentation is here: https://qgrid.readthedocs.io/en/latest/#qgrid.show_grid.
    it's essentially for data analysis
    """
        return qgrid.show_grid(df, show_toolbar=True)

    def sendReportEmail(self):
    """
    Inputs: 
    Output:
    Process: it sends an email with the pdf and csv containing the analysis.
    Commands are from Notify.py. 
    """    
        csvName = "processed_data/events_data_frame_{}.csv.gz".format(
            self.runNum)
        Notify().sendPdfEmail(self.pdfName, csvName)

    def sendReportEmailRecovery(self):
    """
    Inputs:
    Output:
    Process: it sends an email with the pdf containing the analysis. however,
    it is subtly different as it doesn't include the pdf. Commands are from
    Notify.py.
    """
        csvName = "processed_data/events_data_frame_{}.csv.gz".format(
            self.runNum)
        Notify().sendEmailRecovery(self.pdfName, csvName)

    def getCompleteCSVOutputFile(self):
    """
    Inputs:
    Output:
    Process: it creates a csv file exlcuding the data seen below (ADC, ADC1, etc.)
    """
        df = self.events_df.copy()
        df.drop('ADC', axis=1, inplace=True)
        df.drop('ADC1', axis=1, inplace=True)
        df.drop('ADC2', axis=1, inplace=True)
        df.drop('ADC3', axis=1, inplace=True)
        df.drop('ADC4', axis=1, inplace=True)
        df.drop('ADC5', axis=1, inplace=True)
        df.drop('ADC6', axis=1, inplace=True)
        df.drop('ADC7', axis=1, inplace=True)
        df.drop('ADC8', axis=1, inplace=True)
        df.drop('ADC9', axis=1, inplace=True)
        df.drop('ADC10', axis=1, inplace=True)
        df.drop('ADC11', axis=1, inplace=True)
        df.drop('TDC', axis=1, inplace=True)
        df.drop('theta_x1', axis=1, inplace=True)
        df.drop('theta_y1', axis=1, inplace=True)
        df.drop('theta_x2', axis=1, inplace=True)
        df.drop('theta_y2', axis=1, inplace=True)
        df.drop('z_angle', axis=1, inplace=True)
        df = self.addRunNumColumn(df)
        df = self.addInfoColumn(df, "ADC0", "ADC_Ch0")
        df.drop('ADC0', axis=1, inplace=True)
        name = "processed_data/events_data_frame_{}.csv.gz".format(self.runNum)
        df.to_csv(name, header=True, index=False, compression='gzip')
        name = "processed_data/events_data_frame_{}.csv".format(self.runNum)
        df.to_csv(name, header=True, index=False)
        print("{} has been created".format(name))

    def getCompleteCSVOutputFile_og(self):
    """
    Inputs:
    Output:
    Process: it creates a csv file excluding ADC and TDC
    """
        df = self.events_df.copy()
        df.drop('ADC', axis=1, inplace=True)
        df.drop('TDC', axis=1, inplace=True)
        df = self.addRunNumColumn(df)
        name = "processed_data/events_data_frame_{}.csv".format(self.runNum)
        df.to_csv(name, header=True, index=False)
        print("{} has been created".format(name))

    def getCSVOutputFile(self, numEvents):
    """
    Inputs: numEvents-int
    Output:
    Process: it adds a single row to a csv file (without the values below)
    """
        df = self.events_df.copy()
        df.drop('ADC', axis=1, inplace=True)
        df.drop('TDC', axis=1, inplace=True)
        df.drop('theta_x1', axis=1, inplace=True)
        df.drop('theta_y1', axis=1, inplace=True)
        df.drop('theta_x2', axis=1, inplace=True)
        df.drop('theta_y2', axis=1, inplace=True)
        df.drop('z_angle', axis=1, inplace=True)
        df = self.addRunNumColumn(df)
        name = "processed_data/run{}.csv".format(self.runNum)
        numEvents += 1
        df.iloc[:numEvents, :].to_csv(name,
                                      header=True,
                                      index=False,
                                      compression='gzip')
        print("{} has been created".format(name))

    def reload(self):
    """
    Inputs:
    Output:
    Process: it resets the datafile to the original datafile with only the measured values (i think) 
    """
        self.events_df = self.og_df

    def generateReport(self):
    """
    Inputs:
    Output:
    Process: it generates a profile report based on the events measured.
    Documentation at https://pandas-profiling.github.io/pandas-profiling/docs/master/rtd/pages/api/_autosummary/pandas_profiling.profile_report.ProfileReport.html
    """
        profile = ProfileReport(self.events_df,
                                title='Prototype 1B Profiling Report',
                                explorative=True)
        profile.to_file("mdf.html")

    def getStartTime(self):
    """
    Inputs:
    Output: string
    Process: it returns the time of the first event
    """
        x = self.events_df['event_time'].values[0]
        x = pd.to_datetime(str(x))
        return x.strftime("%b %d %Y %H:%M:%S")

    def getEndTime(self):
    """
    Inputs:
    Output: string
    Process: it returns the time of the last event
    """
        x = self.events_df['event_time'].values[-1]
        x = pd.to_datetime(str(x))
        return x.strftime("%b %d %Y %H:%M:%S")

    def getFrontPageInfo(self):
    """
    Inputs:
    Output: string
    Process: it returns a string contained the runNum, start time, end time and report generation time
    """
        fLine = "Analysis of Run: " + self.runNum
        sLine = "\nRun Start: " + str(self.getStartTime())
        tLine = "\nRun End: " + str(self.getEndTime())
        foLine = "\n\n\n\nReport Generated at: " + str(
            datetime.datetime.today().strftime("%b %d %Y %H:%M:%S"))
        txt = fLine + sLine + tLine + foLine
        return txt

    def getMuSpeedPlot(self, pdf=False):
    """
    Inputs:
    Output: graph (i think)
    Process: it creates a histogram of the speed of muons in the range 0 to 1c 
    """
        x = self.getHistogram("speed", range=[0, 1], pdf=pdf)
        return x

    def generateAnaReport(self, pdfName="", reload=True):
    """
    Inputs:
    Output:
    Process: it creates a report pdf to be used in other functions
    """
        print("Creating the report pdf...")
        if pdfName == "":
            pdfName = self.pdfName
        with PdfPages(pdfName) as pdf:
            firstPage = plt.figure(figsize=(11.69, 8.27))
            firstPage.clf()
            txt = self.getFrontPageInfo()
            firstPage.text(0.5,
                           0.5,
                           txt,
                           transform=firstPage.transFigure,
                           size=24,
                           ha="center")
            pdf.savefig()
            plt.close()
            self.getDeadtimePlot(pdf=True)
            pdf.savefig()
            plt.close()
            self.getChannelStatusPlot(pdf=True)
            pdf.savefig()
            plt.close()
            self.getNumLayersHitPlot(pdf=True)
            pdf.savefig()
            plt.close()
            self.getPDFPlot("ADC0", 100, [0, 100], "ADC Channel 0", pdf=True)
            pdf.savefig()
            plt.close()
            try:
                self.getADCPlots(pdf=True)
                pdf.savefig()
                plt.close()
            except:
                pass
            self.getScalerPlots_header(pdf=True)
            pdf.savefig()
            plt.close()
            self.getScalerPlots_channels(pdf=True)
            pdf.savefig()
            plt.close()
            try:
                self.getSmallCounterPlot(pdf=True)
                pdf.savefig()
                plt.close()
            except:
                pass
            self.getCounterPlots(pdf=True)
            pdf.savefig()
            plt.close()
            self.getChannelPlots(pdf=True)
            pdf.savefig()
            plt.close()
            self.getChannelSumPlots(pdf=True, isBinned=True)
            pdf.savefig()
            plt.close()
            self.getChannelDiffPlots(pdf=True, isBinned=True)
            pdf.savefig()
            plt.close()
            self.getAsymmetry1DPlots(pdf=True, isBinned=True, nbin=100)
            pdf.savefig()
            plt.close()
            self.getMuSpeedPlot(pdf=True)
            pdf.savefig()
            plt.close()
            # self.getAsymmetry1DPlotsWithGoodTDCEvents(dev=1,
            # pdf=True,
            # isBinned=True,
            # nbin=150)
            # pdf.savefig()
            # plt.close()
            try:
                self.getXView(pdf=True, reload=reload)
                pdf.savefig()
                plt.close()
                self.getYView(pdf=True, reload=reload)
                pdf.savefig()
                plt.close()
                self.getZView(pdf=True, reload=reload)
                pdf.savefig()
                plt.close()
            except:
                pass

            d = pdf.infodict()
            d['Title'] = 'Prototype 1B Data Analysis'
            d['Author'] = 'Sadman Ahmed Shanto'
            d['Subject'] = 'Storing Analysis Results'
            d['Keywords'] = 'Muon APDL'
            d['CreationDate'] = datetime.datetime.today()
            d['ModDate'] = datetime.datetime.today()

        self.get2DTomogram(pdfv=True, reload=reload)
        self.get2DTomogram(pdfv=True,
                           nbins=50,
                           title="(High Binning)",
                           reload=reload)
        self.getFingerPlots(pdfv=True)
        self.allLayerCorrelationPlots(pdfv=True,
                                      nbins=1000,
                                      title="(High Binning)")
        self.allLayerCorrelationPlots(pdfv=True, nbins=22, title="(Bins = 22)")
        self.convertPNG2PDF()
        self.createOnePDF(pdfName)
        # self.mergePDF(pdfName)
        try:
            os.system(
                "./cpdf -add-text \"Run {}\" -topright 8  {} -o {}".format(
                    self.runNum, pdfName, pdfName))
        except:
            os.system("cpdf -add-text \"Run {}\" -topright 8  {} -o {}".format(
                self.runNum, pdfName, pdfName))
        print("The report file {} has been created.".format(pdfName))

    def generateAsymTestReport(self, pdfName=""):
    """
    Inputs:
    Output:
    Process: it creates histograms for the asymmetry values
    """
        print("Creating the report pdf...")
        if pdfName == "":
            pdfName = self.pdfName
        with PdfPages(pdfName) as pdf:
            firstPage = plt.figure(figsize=(11.69, 8.27))
            firstPage.clf()
            txt = self.getFrontPageInfo()
            firstPage.text(0.5,
                           0.5,
                           txt,
                           transform=firstPage.transFigure,
                           size=24,
                           ha="center")
            pdf.savefig()
            plt.close()
            self.getAsymmetry1DPlots(pdf=True, isBinned=True, nbin=100)
            pdf.savefig()
            plt.close()
            self.getHistogram("asymL1",
                              title="Tray 1",
                              nbins=50,
                              pdf=True,
                              range=(-0.25, 0.25))
            pdf.savefig()
            plt.close()
            self.getHistogram("asymL2",
                              title="Tray 2",
                              nbins=50,
                              pdf=True,
                              range=(-0.25, 0.25))
            pdf.savefig()
            plt.close()
            self.getHistogram("asymL3",
                              title="Tray 3",
                              nbins=50,
                              pdf=True,
                              range=(-0.25, 0.25))
            pdf.savefig()
            plt.close()
            self.getHistogram("asymL4",
                              title="Tray 4",
                              nbins=50,
                              pdf=True,
                              range=(-0.25, 0.25))
            pdf.savefig()
            plt.close()

            d = pdf.infodict()
            d['Title'] = 'Prototype 1B Data Analysis'
            d['Author'] = 'Sadman Ahmed Shanto'
            d['Subject'] = 'Storing Analysis Results'
            d['Keywords'] = 'Muon APDL'
            d['CreationDate'] = datetime.datetime(2020, 12, 21)
            d['ModDate'] = datetime.datetime.today()

        print("The report file {} has been created.".format(pdfName))

    def keepGoodTDCEventsPlot(self, dev=1):
    """
    Inputs:
    Output:
    Process: it filters out events which have a sum more than 1 away from the mean.
    """
        self.keepEvents("sumL1", self.getStats("sumL1")['mean'] + dev, "<=")
        self.keepEvents("sumL1", self.getStats("sumL1")['mean'] - dev, ">=")
        self.keepEvents("sumL2", self.getStats("sumL2")['mean'] + dev, "<=")
        self.keepEvents("sumL2", self.getStats("sumL2")['mean'] - dev, ">=")
        self.keepEvents("sumL3", self.getStats("sumL3")['mean'] + dev, "<=")
        self.keepEvents("sumL3", self.getStats("sumL3")['mean'] - dev, ">=")
        self.keepEvents("sumL4", self.getStats("sumL4")['mean'] + dev, "<=")
        self.keepEvents("sumL4", self.getStats("sumL4")['mean'] - dev, ">=")

    def keep4by4Events(self):
    """
    Inputs:
    Output:
    Process: it filters out events which did not hit all 8 plates
    """
        self.keepEvents("numLHit", 8, "==")

def getXView(self,
                 pdf=False,
                 isBinned=True,
                 nbin=90,
                 a_min=-180,
                 a_max=180,
                 reload=True):
    """
    Inputs:
    Output: png file
    Process: it creates histograms of theta_x1 and theta_x2 with additional stat info (i think).
    it can return a picture of the graph.
    """
        self.keep4by4Events()
        xmin = a_min
        xmax = a_max
        nbins = self.getBins(xmin, xmax, nbin)
        fig, axes = plt.subplots(nrows=1, ncols=2)
        plt.suptitle("X view")
        ax0, ax1 = axes.flatten()
        ax0.hist(self.events_df['theta_x1'], nbins, histtype='step')
        ax0.set_xlim([xmin, xmax])
        s = self.events_df['theta_x1']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Top Tray')
        ax1.hist(self.events_df['theta_x2'], nbins, histtype='step')
        ax1.set_xlim([xmin, xmax])
        ax1.set_title('Bottom Tray')
        s = self.events_df['theta_x2']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.80,
                 0.95,
                 textstr,
                 transform=ax1.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        fig.tight_layout()
        if reload:
            self.reload()
        if not pdf:
            plt.show()
        else:
            return fig

    def getYView(self,
                 pdf=False,
                 isBinned=True,
                 nbin=90,
                 a_min=-180,
                 a_max=180,
                 reload=True):
    """
    Inputs:
    Output: png file
    Process: it creates histograms of theta_y1 and theta_y2 with additional stat info (i think).
    it can return a picture of the graph.
    """
        self.keep4by4Events()
        xmin = a_min
        xmax = a_max
        nbins = self.getBins(xmin, xmax, nbin)
        fig, axes = plt.subplots(nrows=1, ncols=2)
        plt.suptitle("Y view")
        ax0, ax1 = axes.flatten()
        ax0.hist(self.events_df['theta_y1'], nbins, histtype='step')
        ax0.set_xlim([xmin, xmax])
        s = self.events_df['theta_y1']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Top Tray')
        ax1.hist(self.events_df['theta_y2'], nbins, histtype='step')
        ax1.set_xlim([xmin, xmax])
        ax1.set_title('Bottom Tray')
        s = self.events_df['theta_y2']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.80,
                 0.95,
                 textstr,
                 transform=ax1.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        fig.tight_layout()
        if reload:
            self.reload()
        if not pdf:
            plt.show()
        else:
            return fig

    def getThetaXPlot(self,
                      theta_x1,
                      theta_x2,
                      pdf=False,
                      isBinned=True,
                      nbin=90,
                      a_min=-180,
                      a_max=180):
    """
    Inputs: theta_x1,theta_x2-array
    Output: png file
    Process: it creates a histogram of the two values. it can also return the values used for the graph (i think).
    """
        fig, ax = plt.subplots(nrows=1, ncols=2)
        plt.suptitle("X Angle (degrees)")
        ax[0].hist(theta_x1,
                   bins=nbin,
                   range=(a_min, a_max),
                   alpha=0.5,
                   label="Top")
        ax[1].hist(theta_x2,
                   bins=nbin,
                   range=(a_min, a_max),
                   alpha=0.5,
                   label="Bottom")
        plt.legend()
        fig.tight_layout()
        if not pdf:
            plt.show()
        else:
            return ax

    def getThetaYPlot(self,
                      theta_y1,
                      theta_y2,
                      pdf=False,
                      isBinned=True,
                      nbin=90,
                      a_min=-180,
                      a_max=180):
    """
    Inputs: theta_y1,theta_y2-array
    Output: png file
    Process: it creates a histogram of the two values. it can also return the values used in the graph (i think).
    """
        fig, ax = plt.subplots(nrows=1, ncols=2)
        plt.suptitle("Y Angle (degrees)")
        ax[0].hist(theta_y1,
                   bins=nbin,
                   range=(a_min, a_max),
                   alpha=0.5,
                   label="Top")
        ax[1].hist(theta_y2,
                   bins=nbin,
                   range=(a_min, a_max),
                   alpha=0.5,
                   label="Bottom")
        plt.legend()
        if not pdf:
            plt.show()
        else:
            return ax

    def getTomogram(self, pdf=False, isBinned=True, nbin=11, reload=True):
    """
    Inputs:
    Output: png file
    Process: it creates a histogram of the z_angle value. it can also return the figure.
    """
        self.keep4by4Events()
        xmin = -1
        ymin = -1
        xmax = 1
        ymax = 1
        nbins = nbin

        fig, axes = plt.subplots(nrows=1, ncols=1)
        ax0 = axes
        ax0.hist(self.events_df['z_angle'], nbins, histtype='step')
        ax0.set_title('Plane of Lead Brick in Asymmetry Space')
        fig.tight_layout()
        if reload:
            self.reload()
        if not pdf:
            plt.show()
        else:
            return fig

    def getZView(self,
                 pdf=False,
                 isBinned=True,
                 nbin=90,
                 a_min=0,
                 a_max=90,
                 reload=True):
    """
    Inputs:
    Output: png file
    Process: it creates a histogram of the z_angle with additional stat info. it can also return the figure.
    """
        self.keep4by4Events()
        xmin = a_min
        xmax = a_max
        nbins = self.getBins(xmin, xmax, nbin)
        fig, axes = plt.subplots(nrows=1, ncols=1)
        ax0 = axes
        ax0.hist(self.events_df['z_angle'], nbins, histtype='step')
        ax0.set_xlim([xmin, xmax])
        s = self.events_df['z_angle']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=10,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Zenith Angle (4/4 events)')
        fig.tight_layout()
        if reload:
            self.reload()
        if not pdf:
            plt.show()
        else:
            return fig

    def getAsymmetry1DPlotsWithGoodTDCEvents(self,
                                             dev=1,
                                             pdf=False,
                                             isBinned=True,
                                             nbin=150,
                                             amount=5,
                                             xmax=0.5,
                                             xmin=-0.5):
    """
    Inputs:
    Output:
    Process: it creates a histogram of acceptable values (see keepGoodTDCEventsPlot and getAsymmetry1DPlots)
    """
        self.keepGoodTDCEventsPlot(dev)
        self.getAsymmetry1DPlots(
            pdf=pdf,
            isBinned=isBinned,
            nbin=nbin,
            amount=amount,
            title=
            "Histogram of Assymetry of each Tray (Events +- {} of Mean of SumTDC)"
            .format(dev),
            xmax=xmax,
            xmin=xmin)
        self.reload()

    def mergePDF(self, pdfName):
    """
    Inputs: pdfName-string
    Output:
    Process: it adds all pdfs created in pdfList (they are really pages of the same pdf) and merges them into one final pdf.
    """
        for i in self.pdfList:
            os.remove(i + ".png")
        self.pdfList = [i + ".pdf" for i in self.pdfList]
        self.pdfList.insert(0, pdfName)
        output = PdfFileWriter()
        for i in self.pdfList:
            append_pdf(PdfFileReader(file(i, "rb")), output)
        output.write(file(pdfName, "wb"))

    def createOnePDF(self, pdfName):
    """
    Inputs: pdfName-string
    Output:
    Process: it takes out the png files and replaces them with pdfs in pdfList.
    """
        for i in self.pdfList:
            os.remove(i + ".png")
        self.pdfList = [i + ".pdf" for i in self.pdfList]
        self.pdfList.insert(0, pdfName)

        merger = PdfFileMerger()
        for pdf in self.pdfList:
            merger.append(PdfFileReader(pdf), 'rb')
        with open(pdfName, 'wb') as new_file:
            merger.write(new_file)

        # with open(output, 'wb') as f:
        # merger.write(pdfName)
        merger.close()
        self.pdfList.pop(0)
        for i in self.pdfList:
            os.remove(i)

    def convertPNG2PDF(self):
    """
    Inputs:
    Output:
    Process: it creates the pdfs needed for the above function.
    """
        for i in self.pdfList:
            image1 = Image.open(i + ".png")
            im1 = image1.convert('RGB')
            im1.save(i + ".pdf")

    # def gui(self):
    # show(self.events_df, settings={'block': True})
    # show(self.events_df)

    def getAnaReport(self):
    """
    Inputs:
    Output:
    Process: it creates an analysis report including all commands below (see commands for more details).
    """
        self.getDeadtimePlot()
        self.getChannelPlots()
        self.getChannelSumPlots()
        self.getChannelDiffPlots()
        self.getAsymmetry1DPlots()
        self.getNumLayersHitPlot()
        self.allLayerCorrelationPlots(nbins=200)
        self.allLayerCorrelationPlots(nbins=22)
        self.getScalerPlots_header()
        self.getScalerPlots_channels()

    def getScalerPlots_channels(self, pdf=False, amount=5):
    """
    Inputs:
    Output: png file
    Process: it creates histograms for the values of channels 4-11 with additional stat info. it can also return a png file.
    """
        fig, axes = plt.subplots(nrows=4, ncols=2)
        plt.suptitle("Histogram of Scaler Readings (Ch 4 - 11)")
        ax0, ax1, ax2, ax3, ax4, ax5, ax6, ax7 = axes.flatten()
        s = self.events_df['SCh4']
        nbins = round(max(s.values) - min(s.values) // amount)
        ax0.hist(self.events_df['SCh4'], nbins, histtype='step')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Ch4 (1L)')
        s = self.events_df['SCh5']
        nbins = (max(s.values) - min(s.values)) // amount
        ax1.hist(self.events_df['SCh5'], nbins, histtype='step')
        ax1.set_title('Ch5 (1R)')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.80,
                 0.95,
                 textstr,
                 transform=ax1.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        s = self.events_df['SCh6']
        nbins = (max(s.values) - min(s.values)) // amount
        ax2.hist(self.events_df['SCh6'], nbins, histtype='step')
        ax2.set_title('Ch6 (2L)')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax2.text(0.80,
                 0.95,
                 textstr,
                 transform=ax2.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        s = self.events_df['SCh7']
        nbins = (max(s.values) - min(s.values)) // amount
        ax3.hist(self.events_df['SCh7'], nbins, histtype='step')
        ax3.set_title('Ch7 (2R)')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax3.text(0.80,
                 0.95,
                 textstr,
                 transform=ax3.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        s = self.events_df['SCh8']
        nbins = (max(s.values) - min(s.values)) // amount
        ax4.hist(self.events_df['SCh8'], nbins, histtype='step')
        ax4.set_title('Ch8 (3L)')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax4.text(0.80,
                 0.95,
                 textstr,
                 transform=ax4.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        s = self.events_df['SCh9']
        nbins = (max(s.values) - min(s.values)) // amount
        ax5.hist(self.events_df['SCh9'], nbins, histtype='step')
        ax5.set_title('Ch9 (3R)')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax5.text(0.80,
                 0.95,
                 textstr,
                 transform=ax5.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        s = self.events_df['SCh10']
        nbins = (max(s.values) - min(s.values)) // amount
        ax6.hist(self.events_df['SCh9'], nbins, histtype='step')
        ax6.set_title('Ch10 (4L)')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax6.text(0.80,
                 0.95,
                 textstr,
                 transform=ax6.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        s = self.events_df['SCh11']
        nbins = (max(s.values) - min(s.values)) // amount
        ax7.hist(self.events_df['SCh11'], nbins, histtype='step')
        ax7.set_title('Ch11 (4R)')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax7.text(0.80,
                 0.95,
                 textstr,
                 transform=ax7.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        fig.tight_layout()
        if not pdf:
            plt.show()
        else:
            return fig

    def getScalerPlots_header(self, pdf=False, amount=5):
    """
    Inputs:
    Output:
    Process: same as above, but using channels 0-3.
    """
        fig, axes = plt.subplots(nrows=4, ncols=1)
        plt.suptitle("Histogram of Scaler Readings (Ch 0 - 3)")
        ax0, ax1, ax2, ax3 = axes.flatten()
        s = self.events_df['SCh0']
        ax0.hist(self.events_df['SCh0'], 200, histtype='step')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\n".format(
            mean, std, count)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Ch0')
        s = self.events_df['SCh1']
        nbins = (max(s.values) - min(s.values)) // amount
        ax1.hist(self.events_df['SCh1'], nbins, histtype='step')
        ax1.set_title('Ch1')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.80,
                 0.95,
                 textstr,
                 transform=ax1.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        s = self.events_df['SCh2']
        nbins = (max(s.values) - min(s.values)) // amount
        ax2.hist(self.events_df['SCh2'], nbins, histtype='step')
        ax2.set_title('Ch2')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}".format(
            mean, std, count, nbins)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax2.text(0.80,
                 0.95,
                 textstr,
                 transform=ax2.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        s = self.events_df['SCh3']
        ax3.hist(self.events_df['SCh3'], 200, histtype='step')
        ax3.set_title('Ch3')
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\n".format(
            mean, std, count)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax3.text(0.80,
                 0.95,
                 textstr,
                 transform=ax3.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        fig.tight_layout()
        if not pdf:
            plt.show()
        else:
            return fig

    def getAsymPlotFig(self, term1, term2, nbins=500):
    """
    Inputs:
    Output: histogram
    Process: it creates a 2d histogram of the asymmetry in x and y.
    """
        xmin = -0.65
        xmax = 0.65
        ymin = -0.65
        ymax = 0.65
        x = self.get2DHistogram(self.events_df[term1].values,
                                self.events_df[term2].values,
                                "{} vs {}".format(term1, term2),
                                "Asymmetry in X", "Asymmetry in Y", xmin, xmax,
                                ymin, ymax, nbins, True)
        print(x)
        return x

    def x(self, t):
    """
    Inputs: t-float
    Output:
    Process: it is used in an overall asymmetry in x calculation.
    """
        asymT1 = self.events_df["asymL1"].values
        asymT3 = self.events_df["asymL3"].values
        return asymT1 + asymT3 * t

    def y(self, t):
    """
    Inputs: t-float
    Output:
    Process: it is used in an overall asymmetry in y calculation.
    """
        asymT2 = self.events_df["asymL2"].values
        asymT4 = self.events_df["asymL4"].values
        return asymT2 + asymT4 * t

    def z(self, t):
    """
    Inputs: t-float
    Output:
    Process: it uses constants to calculate the z for one of our calculations.
    """
        return -(self.d_phys / 2) + self.d_phys * t

    def getTValue(self):
    """
    Inputs:
    Output: float
    Process: it performs a calculation for the t value used above based on constants of our experiment. can be changed easily to accomodate other setups. 
    """
        phys = -(self.d_phys / 2) - self.d_lead
        return getAsymmetryUnits(phys)

    def get2DTomogram(self, pdfv=False, nbins=11, title="", reload=True):
    """
    Inputs:
    Output: 
    Process: creates 2D histogram of x and y asymmetry changed by the t value in our experiment.
    """
        self.keep4by4Events()
        xmin = -1
        xmax = 1
        ymin = -1
        ymax = 1
        t = self.getTValue()
        xx = self.x(t)
        yy = self.y(t)
        self.get2DHistogram(xx,
                            yy,
                            "{} Z Plane of Lead Brick".format(title),
                            "Asymmetry in X",
                            "Asymmetry in Y",
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv,
                            zLog=False)
        if reload:
            self.reload()
        else:
            pass

    def getCorrelationPlot(self, query_list, nbins=1000, title=""):
    """
    Inputs: query_list-datafile
    Output:
    Process: it creates a 2d histogram of a given query_list dataset. i'm honestly not sure how it is used. i couldn't find any
    other references to it or query_list.
    """
        xmin = -0.65
        xmax = 0.65
        ymin = -0.65
        ymax = 0.65
        self.get2DHistogram(self.events_df[query_list[0]].values,
                            self.events_df[query_list[1]].values,
                            "{}".format(title), "{}".format(query_list[0]),
                            "{}".format(query_list[1]), xmin, xmax, ymin, ymax,
                            nbins, False)

    def allLayerCorrelationPlots(self, pdfv=False, nbins=1000, title=""):
    """
    Inputs:
    Output:
    Process: it creates histograms for all asymmetry value combinations.
    """
        xmin = -0.65
        xmax = 0.65
        ymin = -0.65
        ymax = 0.65
        self.get2DHistogram(self.events_df['asymL1'].values,
                            self.events_df['asymL2'].values,
                            "{} Asymmetry: L1 vs L2".format(title),
                            "Asymmetry in X",
                            "Asymmetry in Y",
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)
        self.get2DHistogram(self.events_df['asymL3'].values,
                            self.events_df['asymL4'].values,
                            "{} Asymmetry: L3 vs L4".format(title),
                            "Asymmetry in X",
                            "Asymmetry in Y",
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)
        self.get2DHistogram(self.events_df['asymL1'].values,
                            self.events_df['asymL3'].values,
                            "{} Asymmetry: L1 vs L3".format(title),
                            "Asymmetry in X",
                            "Asymmetry in Y",
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)
        self.get2DHistogram(self.events_df['asymL2'].values,
                            self.events_df['asymL4'].values,
                            "{} Asymmetry: L2 vs L4".format(title),
                            "Asymmetry in X",
                            "Asymmetry in Y",
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)
        self.get2DHistogram(self.events_df['asymL1'].values,
                            self.events_df['asymL4'].values,
                            "{} Asymmetry: L1 vs L4".format(title),
                            "Asymmetry in X",
                            "Asymmetry in Y",
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)
        self.get2DHistogram(self.events_df['asymL2'].values,
                            self.events_df['asymL3'].values,
                            "{} Asymmetry: L2 vs L3".format(title),
                            "Asymmetry in X",
                            "Asymmetry in Y",
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)

    def getFingerPlots(self, pdfv=False):
    """
    Inputs:
    Output:
    Process: it creates histograms of L and R values (only matching numbers).
    """
        xmin = 0
        xmax = 300
        ymin = -0
        ymax = 300
        nbins = 250
        x = "L1"
        y = "R1"
        self.get2DHistogram(self.events_df[x].values,
                            self.events_df[y].values,
                            "{} vs {}".format(x, y),
                            x,
                            y,
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)
        x = "L2"
        y = "R2"
        self.get2DHistogram(self.events_df[x].values,
                            self.events_df[y].values,
                            "{} vs {}".format(x, y),
                            x,
                            y,
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)
        x = "L3"
        y = "R3"
        self.get2DHistogram(self.events_df[x].values,
                            self.events_df[y].values,
                            "{} vs {}".format(x, y),
                            x,
                            y,
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)
        x = "L4"
        y = "R4"
        self.get2DHistogram(self.events_df[x].values,
                            self.events_df[y].values,
                            "{} vs {}".format(x, y),
                            x,
                            y,
                            xmin,
                            xmax,
                            ymin,
                            ymax,
                            nbins,
                            pdf=pdfv)

    def getDeadtimePlot(self, pdf=False):
    """
    Inputs:
    Output:
    Process: it creates a histogram of deadtime.
    """
        x = self.getHistogram("deadtime", pdf=pdf)
        return x

    def getPDFPlot(self, term, nbin, range, title="", pdf=False):
    """
    Inputs: term-string
    Output: figure
    Process: it creates a histogram of a given term and finds standard stat info on it.
    """
        xmin, xmax = range
        nbins = self.getBins(xmin, xmax, nbin)
        fig, ax = plt.subplots(nrows=1, ncols=1)
        ax.hist(self.events_df[term], nbins, histtype='step')
        ax.set_xlim([xmin, xmax])
        s = self.events_df[term]
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.80,
                0.95,
                textstr,
                transform=ax.transAxes,
                fontsize=5,
                verticalalignment='top',
                bbox=props)
        ax.set_title(title)
        ax.set_yscale('log')
        fig.tight_layout()
        return fig

    def getEfficiencyPlot(self, pdf=False):
    """
    Inputs:
    Output: string
    Process: it sets up an empty string ax
    """
        ax = ""
        return ax

    def getChannelStatusPlot(self, pdf=False):
    """
    Inputs:
    Output: plot array (i think)
    Process: it populates the previous ax with plots of the efficiency with which
    we get viable datapoints.
    """
    
        l1_p = list(self.og_df['l1hit'].values).count(1)
        l2_p = list(self.og_df['l2hit'].values).count(1)
        l3_p = list(self.og_df['l3hit'].values).count(1)
        l4_p = list(self.og_df['l4hit'].values).count(1)

        r1_p = list(self.og_df['r1hit'].values).count(1)
        r2_p = list(self.og_df['r2hit'].values).count(1)
        r3_p = list(self.og_df['r3hit'].values).count(1)
        r4_p = list(self.og_df['r4hit'].values).count(1)

        yvals = [
            l1_p / self.total, r1_p / self.total, l2_p / self.total,
            r2_p / self.total, l3_p / self.total, r3_p / self.total,
            l4_p / self.total, r4_p / self.total
        ]
        yvals = [i * 100 for i in yvals]
        xvals = [
            "Ch 0", "Ch 1", "Ch 2", "Ch 3", "Ch 6", "Ch 7", "Ch 8", "Ch 9"
        ]
        barlist = plt.bar(xvals, yvals)
        barlist[0].set_color('r')
        barlist[1].set_color('r')
        barlist[4].set_color('r')
        barlist[5].set_color('r')
        plt.title("Percentage of Good Events")
        plt.ylim(0, 100)
        ax = barlist
        if not pdf:
            plt.show()
        else:
            return ax

    def getNumLayersHitPlot(self, pdf=False):
    """
    Inputs:
    Output:
    Process: it creates a histogram of the number of plates hit in events (out of 8).
    """
        x = self.getHistogram("numLHit",
                              title="(TDC Hits Registered Per Event)",
                              pdf=pdf)
        return x

    def getBins(self, xmin, xmax, nbins):
    """
    Inputs: xmin,xmax-float, nbins-int
    Output: array
    Process: it finds the delimiations necessary in a dataset for a given bin count.
    Ex.: a set going from 0 to 10 with 10 bins requires each bin to have a size of 1.
    it returns an array cotaining every n elements of the starting array.
    """
        x = list(range(xmin, xmax))
        n = round((xmax - xmin) / nbins)
        return x[::n]

    def getSmallCounterPlot(self, pdf=False, nbin=100):
    """
    Inputs:
    Output: png file
    Process: it creates a histogram of the 8th value of the TDC. i'm not sure what this value actually is (i think).
    """
        xmin = 0
        xmax = 400
        nbins = self.getBins(xmin, xmax, nbin)
        fig, axes = plt.subplots(nrows=1, ncols=1)
        ax0 = axes
        ax0.hist(self.events_df['SmallCounter'], nbins, histtype='step')
        ax0.set_xlim([xmin, xmax])
        s = self.events_df['SmallCounter']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=10,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Small Counter')
        fig.tight_layout()
        if not pdf:
            plt.show()
        else:
            return fig

    def getCounterPlots(self, pdf=False, nbin=100):
    """
    Inputs:
    Output: png file
    Process: it creates a histogram of top counter and one of bottom counter.
    """
        xmin = 0
        xmax = 200
        nbins = self.getBins(xmin, xmax, nbin)
        fig, axes = plt.subplots(nrows=1, ncols=2)
        plt.suptitle("Top and Bottom Counters")
        ax0, ax1 = axes.flatten()
        ax0.hist(self.events_df['TopCounter'], nbins, histtype='step')
        ax0.set_xlim([xmin, xmax])
        s = self.events_df['TopCounter']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Top Counter')
        ax1.hist(self.events_df['BottomCounter'], nbins, histtype='step')
        ax1.set_xlim([xmin, xmax])
        ax1.set_title('Bottom Counter')
        s = self.events_df['BottomCounter']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.80,
                 0.95,
                 textstr,
                 transform=ax1.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        fig.tight_layout()
        if not pdf:
            plt.show()
        else:
            return fig

    def getMuonRate(self, mu_num_thresh_hold, pdf=False):
    """
    Inputs: mu_num_thresh_hold-float
    Output:
    Process: it creates a pair of scatter plots and histograms of muon rates, one for daytime events and one for nighttime.
    """
        self.classifyDateTime()
        self.getSerializedTimes()
        ms2min = 1.6666666666666667 * 10**(-8)
        times = self.get("time") * ms2min
        mu_num = self.get("event_num")
        colors = [
            'red' if x == "day" else 'blue' for x in self.get("time_of_day")
        ]
        time_arr = []
        color = []
        for i in range(len(mu_num)):
            if mu_num[i] % mu_num_thresh_hold == 0:
                time_arr.append(times[i])
                color.append(colors[i])

        time_diff = np.diff(np.array(time_arr))
        mu_rate = np.array(mu_num_thresh_hold / time_diff)
        xvals = np.array([i for i in range(len(mu_rate))])

        day = np.array(color) == "red"
        night = np.array(color) == "blue"

        fig, axes = plt.subplots(nrows=1, ncols=2)
        plt.suptitle("Muon Rate (number/min)")
        ax0, ax1 = axes.flatten()

        ax0.scatter(xvals[day[1:]],
                    mu_rate[day[1:]],
                    color='orange',
                    label="day",
                    s=0.9)
        ax0.scatter(xvals[night[1:]],
                    mu_rate[night[1:]],
                    color='blue',
                    label="night",
                    s=0.9)
        ax0.legend()
        ax0.set_xlabel("Number of times 1000 muons were recorded")
        ax0.set_ylabel("Muon Rate")
        ax1.hist(mu_rate[night[1:]], label="night", histtype="step", bins=15)
        ax1.hist(mu_rate[day[1:]], label="day", histtype="step", bins=15)
        ax1.set_xlabel("Muon Rate")
        plt.legend()
        fig.tight_layout()
        self.events_df = self.og_df
        if not pdf:
            plt.show()
        else:
            return fig

    def getADCPlots(self, pdf=False, nbin=10):
    """
    Inputs: 
    Output: png file
    Process: it creates histograms of ADC 0-11. it also returns a figure of them.
    """
        xmin = 0
        xmax = 30
        # nbins = self.getBins(xmin, xmax, nbin)
        nbins = nbin
        fig, axes = plt.subplots(nrows=3, ncols=4)
        plt.suptitle("Histogram of All ADC Channels")
        ax0, ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9, ax10, ax11 = axes.flatten(
        )

        ax0.hist(self.events_df['ADC0'], nbins, histtype='step')
        # ax0.set_xlim([xmin, xmax])
        s = self.events_df['ADC0']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Ch0')
        ax1.hist(self.events_df['ADC1'], nbins, histtype='step')
        ax1.set_xlim([xmin, xmax])
        ax1.set_title('Ch1')
        s = self.events_df['ADC1']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.80,
                 0.95,
                 textstr,
                 transform=ax1.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax2.hist(self.events_df['ADC2'], nbins, histtype='step')
        ax2.set_title('Ch2')
        ax2.set_xlim([xmin, xmax])
        s = self.events_df['ADC2']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax2.text(0.80,
                 0.95,
                 textstr,
                 transform=ax2.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax3.hist(self.events_df['ADC3'], nbins, histtype='step')
        ax3.set_xlim([xmin, xmax])
        ax3.set_title('Ch3')
        s = self.events_df['ADC3']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax3.text(0.80,
                 0.95,
                 textstr,
                 transform=ax3.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax4.hist(self.events_df['ADC4'], nbins, histtype='step')
        ax4.set_xlim([xmin, xmax])
        ax4.set_title('Ch4')
        s = self.events_df['ADC4']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax4.text(0.80,
                 0.95,
                 textstr,
                 transform=ax4.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax5.hist(self.events_df['ADC5'], nbins, histtype='step')
        ax5.set_xlim([xmin, xmax])
        ax5.set_title('Ch5')
        s = self.events_df['ADC5']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax5.text(0.80,
                 0.95,
                 textstr,
                 transform=ax5.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax6.hist(self.events_df['ADC6'], nbins, histtype='step')
        ax6.set_xlim([xmin, xmax])
        ax6.set_title('Ch6')
        s = self.events_df['ADC6']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax6.text(0.80,
                 0.95,
                 textstr,
                 transform=ax6.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax7.hist(self.events_df['ADC7'], nbins, histtype='step')
        ax7.set_xlim([xmin, xmax])
        ax7.set_title('Ch7')
        s = self.events_df['ADC7']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax7.text(0.80,
                 0.95,
                 textstr,
                 transform=ax7.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax8.hist(self.events_df['ADC8'], nbins, histtype='step')
        ax8.set_xlim([xmin, xmax])
        ax8.set_title('Ch8')
        s = self.events_df['ADC8']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax8.text(0.80,
                 0.95,
                 textstr,
                 transform=ax8.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax9.hist(self.events_df['ADC9'], nbins, histtype='step')
        ax9.set_xlim([xmin, xmax])
        ax9.set_title('Ch9')
        s = self.events_df['ADC9']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax9.text(0.80,
                 0.95,
                 textstr,
                 transform=ax9.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax10.hist(self.events_df['ADC10'], nbins, histtype='step')
        ax10.set_xlim([xmin, xmax])
        ax10.set_title('Ch10')
        s = self.events_df['ADC10']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax10.text(0.80,
                  0.95,
                  textstr,
                  transform=ax10.transAxes,
                  fontsize=5,
                  verticalalignment='top',
                  bbox=props)
        ax11.hist(self.events_df['ADC11'], nbins, histtype='step')
        ax11.set_xlim([xmin, xmax])
        ax11.set_title('Ch11')
        s = self.events_df['ADC11']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax11.text(0.80,
                  0.95,
                  textstr,
                  transform=ax11.transAxes,
                  fontsize=5,
                  verticalalignment='top',
                  bbox=props)
        fig.tight_layout()
        if not pdf:
            plt.show()
        else:
            return fig

    def getChannelPlots(self, pdf=False, nbin=200):
        "Inputs: self-> not sure, pdf=False->string, nbin =10->int"
        "Outputs: 12 different ADC channel histograms"
        "Process: the code takes each individual channel and plots its hisogram, its axes and the mean standard
        "deviation, all from the nhmber of muon events that specific channel picked up, and then displays them all"
        xmin = 0
        xmax = 200
        nbins = self.getBins(xmin, xmax, nbin)
        fig, axes = plt.subplots(nrows=2, ncols=4)
        plt.suptitle("Histogram of All Individual Channels")
        ax0, ax1, ax2, ax3, ax4, ax5, ax6, ax7 = axes.flatten()
        ax0.hist(self.events_df['L1'], nbins, histtype='step')
        ax0.set_xlim([xmin, xmax])
        s = self.events_df['L1']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax0.text(0.80,
                 0.95,
                 textstr,
                 transform=ax0.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax0.set_title('Ch0')
        ax1.hist(self.events_df['R1'], nbins, histtype='step')
        ax1.set_xlim([xmin, xmax])
        ax1.set_title('Ch1')
        s = self.events_df['R1']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax1.text(0.80,
                 0.95,
                 textstr,
                 transform=ax1.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax2.hist(self.events_df['L2'], nbins, histtype='step')
        ax2.set_title('Ch2')
        ax2.set_xlim([xmin, xmax])
        s = self.events_df['L2']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax2.text(0.80,
                 0.95,
                 textstr,
                 transform=ax2.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax3.hist(self.events_df['R2'], nbins, histtype='step')
        ax3.set_xlim([xmin, xmax])
        ax3.set_title('Ch3')
        s = self.events_df['R2']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax3.text(0.80,
                 0.95,
                 textstr,
                 transform=ax3.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax4.hist(self.events_df['L3'], nbins, histtype='step')
        ax4.set_xlim([xmin, xmax])
        ax4.set_title('Ch6')
        s = self.events_df['L3']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax4.text(0.80,
                 0.95,
                 textstr,
                 transform=ax4.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax5.hist(self.events_df['R3'], nbins, histtype='step')
        ax5.set_xlim([xmin, xmax])
        ax5.set_title('Ch7')
        s = self.events_df['R3']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax5.text(0.80,
                 0.95,
                 textstr,
                 transform=ax5.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax6.hist(self.events_df['L4'], nbins, histtype='step')
        ax6.set_xlim([xmin, xmax])
        ax6.set_title('Ch8')
        s = self.events_df['L4']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax6.text(0.80,
                 0.95,
                 textstr,
                 transform=ax6.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        ax7.hist(self.events_df['R4'], nbins, histtype='step')
        ax7.set_xlim([xmin, xmax])
        ax7.set_title('Ch9')
        s = self.events_df['R4']
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        ovflow = ((xmax < s.values) | (s.values < xmin)).sum()
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBins: {}\nOverflow: {}".format(
            mean, std, count, nbin, ovflow)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax7.text(0.80,
                 0.95,
                 textstr,
                 transform=ax7.transAxes,
                 fontsize=5,
                 verticalalignment='top',
                 bbox=props)
        fig.tight_layout()
        if not pdf:
            plt.show()
        else:
            return fig

    def getChannelSumPlots(self, pdf=False, isBinned=True, nbin=50, amount=5):
        "Inputs: self-> string, pdf=False-> string, isBinned=True-> boolean, nbin=50-> int, amount=5-> int "
        "Outputs: 4 histograms that show mean, standard deviation, and overflow from the number of muon events"
        "Process: The code checks the value  of the boolean input(isBinned) and if true, The code  then takes 
        "the left cable(L) of a given tray's combined TDC value and then plots it. the code makes an array
        "of 4 rows and 1 column of different histograms, each histogram has its mean, std, and overflow listed. 
        if isBinned:
            fig, axes = plt.subplots(nrows=4, ncols=1)
            xmin, xmax = 160, 280
            nbins = self.getBins(xmin, xmax, nbin)
            plt.suptitle(
                "Histogram of Sum of Channels in their Respective Trays")
            ax0, ax1, ax2, ax3 = axes.flatten()
            ovflow = ((xmax < self.events_df['sumL1'].values) |
                      (self.events_df['sumL1'].values < xmin)).sum()
            ax0.hist(self.events_df['sumL1'], bins=nbins, histtype='step')
            ax0.set_xlim([xmin, xmax])
            s = self.events_df['sumL1']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax0.text(0.90,
                     0.95,
                     textstr,
                     transform=ax0.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ax0.set_title('Tray 1')
            ovflow = ((xmax < self.events_df['sumL2'].values) |
                      (self.events_df['sumL2'].values < xmin)).sum()
            ax1.hist(self.events_df['sumL2'], nbins, histtype='step')
            ax1.set_xlim([xmin, xmax])
            ax1.set_title('Tray 2')
            s = self.events_df['sumL2']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax1.text(0.90,
                     0.95,
                     textstr,
                     transform=ax1.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ovflow = ((xmax < self.events_df['sumL3'].values) |
                      (self.events_df['sumL3'].values < xmin)).sum()
            ax2.hist(self.events_df['sumL3'], nbins, histtype='step')
            ax2.set_xlim([xmin, xmax])
            ax2.set_title('Tray 3')
            s = self.events_df['sumL3']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax2.text(0.90,
                     0.95,
                     textstr,
                     transform=ax2.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ovflow = ((xmax < self.events_df['sumL4'].values) |
                      (self.events_df['sumL4'].values < xmin)).sum()
            ax3.hist(self.events_df['sumL4'], nbins, histtype='step')
            ax3.set_xlim([xmin, xmax])
            ax3.set_title('Tray 4')
            s = self.events_df['sumL4']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax3.text(0.90,
                     0.95,
                     textstr,
                     transform=ax3.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            fig.tight_layout()
            if not pdf:
                plt.show()
            else:
                return fig
        else:
            fig, axes = plt.subplots(nrows=4, ncols=1)
            xmin, xmax = 150, 250
            plt.suptitle(
                "Histogram of Sum of Channels in their Respective Trays")
            ax0, ax1, ax2, ax3 = axes.flatten()
            nbins = len(self.events_df['sumL1']) // amount
            ovflow = ((xmax < self.events_df['sumL1'].values) |
                      (self.events_df['sumL1'].values < xmin)).sum()
            ax0.hist(self.events_df['sumL1'], bins=nbins, histtype='step')
            ax0.set_xlim([xmin, xmax])
            s = self.events_df['sumL1']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax0.text(0.90,
                     0.95,
                     textstr,
                     transform=ax0.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ax0.set_title('Tray 1')
            nbins = len(self.events_df['sumL2']) // amount
            ovflow = ((xmax < self.events_df['sumL2'].values) |
                      (self.events_df['sumL2'].values < xmin)).sum()
            ax1.hist(self.events_df['sumL2'], nbins, histtype='step')
            ax1.set_xlim([xmin, xmax])
            ax1.set_title('Tray 2')
            s = self.events_df['sumL2']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax1.text(0.90,
                     0.95,
                     textstr,
                     transform=ax1.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            nbins = len(self.events_df['sumL3']) // amount
            ovflow = ((xmax < self.events_df['sumL3'].values) |
                      (self.events_df['sumL3'].values < xmin)).sum()
            ax2.hist(self.events_df['sumL3'], nbins, histtype='step')
            ax2.set_xlim([xmin, xmax])
            ax2.set_title('Tray 3')
            s = self.events_df['sumL3']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax2.text(0.90,
                     0.95,
                     textstr,
                     transform=ax2.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            nbins = len(self.events_df['sumL4']) // amount
            ovflow = ((xmax < self.events_df['sumL4'].values) |
                      (self.events_df['sumL4'].values < xmin)).sum()
            ax3.hist(self.events_df['sumL4'], nbins, histtype='step')
            ax3.set_xlim([xmin, xmax])
            ax3.set_title('Tray 4')
            s = self.events_df['sumL4']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax3.text(0.90,
                     0.95,
                     textstr,
                     transform=ax3.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            fig.tight_layout()
            if not pdf:
                plt.show()
            else:
                return fig

    def getChannelDiffPlots(self, pdf=False, isBinned=True, nbin=50, amount=5):
        "Inputs: self-> string, pdf=False-> boolean, isBinned=True-> boolean, nbin=50-> int, amount=5-> int 
        "Outputs: 4 histograms with mean, standard deviation and overflow listed
        "Process: the code checks to see if the isBinned is true, if so, the code makes a histogram with a range of 200 
        " units from -100 to 100 and subtracts the values of anything less than the xmin and greater than xmax and subtracts them. 
        " The values come fronm the left cable of a given tray. If the value of isBinned is false, then the code does the same thing"
        if isBinned:
            fig, axes = plt.subplots(nrows=4, ncols=1)
            xmin = -100
            xmax = 100
            plt.suptitle(
                "Histogram of Difference of Channels in their Respective Trays"
            )
            nbins = self.getBins(xmin, xmax, nbin)
            ovflow = ((xmax < self.events_df['diffL1'].values) |
                      (self.events_df['diffL1'].values < xmin)).sum()
            ax0, ax1, ax2, ax3 = axes.flatten()
            ax0.hist(self.events_df['diffL1'], nbins, histtype='step')
            ax0.set_xlim([xmin, xmax])
            s = self.events_df['diffL1']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax0.text(0.90,
                     0.95,
                     textstr,
                     transform=ax0.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ax0.set_title('Tray 1')
            ovflow = ((xmax < self.events_df['diffL2'].values) |
                      (self.events_df['diffL2'].values < xmin)).sum()
            ax1.hist(self.events_df['diffL2'], nbins, histtype='step')
            ax1.set_xlim([xmin, xmax])
            ax1.set_title('Tray 2')
            s = self.events_df['diffL2']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax1.text(0.90,
                     0.95,
                     textstr,
                     transform=ax1.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ovflow = ((xmax < self.events_df['diffL3'].values) |
                      (self.events_df['diffL3'].values < xmin)).sum()
            ax2.hist(self.events_df['diffL3'], nbins, histtype='step')
            ax2.set_xlim([xmin, xmax])
            ax2.set_title('Tray 3')
            s = self.events_df['diffL3']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax2.text(0.90,
                     0.95,
                     textstr,
                     transform=ax2.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ovflow = ((xmax < self.events_df['diffL4'].values) |
                      (self.events_df['diffL4'].values < xmin)).sum()
            ax3.hist(self.events_df['diffL4'], nbins, histtype='step')
            ax3.set_xlim([xmin, xmax])
            ax3.set_title('Tray 4')
            s = self.events_df['diffL4']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax3.text(0.90,
                     0.95,
                     textstr,
                     transform=ax3.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            fig.tight_layout()
            if not pdf:
                plt.show()
            else:
                return fig
        else:
            fig, axes = plt.subplots(nrows=4, ncols=1)
            xmin = -100
            xmax = 100
            plt.suptitle(
                "Histogram of Difference of Channels in their Respective Trays"
            )
            nbins = len(self.events_df['diffL1']) // amount
            ovflow = ((xmax < self.events_df['diffL1'].values) |
                      (self.events_df['diffL1'].values < xmin)).sum()
            ax0, ax1, ax2, ax3 = axes.flatten()
            ax0.hist(self.events_df['diffL1'], nbins, histtype='step')
            ax0.set_xlim([xmin, xmax])
            s = self.events_df['diffL1']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax0.text(0.90,
                     0.95,
                     textstr,
                     transform=ax0.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ax0.set_title('Tray 1')
            nbins = len(self.events_df['diffL2']) // amount
            ovflow = ((xmax < self.events_df['diffL2'].values) |
                      (self.events_df['diffL2'].values < xmin)).sum()
            ax1.hist(self.events_df['diffL2'], nbins, histtype='step')
            ax1.set_xlim([xmin, xmax])
            ax1.set_title('Tray 2')
            s = self.events_df['diffL2']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax1.text(0.90,
                     0.95,
                     textstr,
                     transform=ax1.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            nbins = len(self.events_df['diffL3']) // amount
            ovflow = ((xmax < self.events_df['diffL3'].values) |
                      (self.events_df['diffL3'].values < xmin)).sum()
            ax2.hist(self.events_df['diffL3'], nbins, histtype='step')
            ax2.set_xlim([xmin, xmax])
            ax2.set_title('Tray 3')
            s = self.events_df['diffL3']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax2.text(0.90,
                     0.95,
                     textstr,
                     transform=ax2.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            nbins = len(self.events_df['diffL4']) // amount
            ovflow = ((xmax < self.events_df['diffL4'].values) |
                      (self.events_df['diffL4'].values < xmin)).sum()
            ax3.hist(self.events_df['diffL4'], nbins, histtype='step')
            ax3.set_xlim([xmin, xmax])
            ax3.set_title('Tray 4')
            s = self.events_df['diffL4']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax3.text(0.90,
                     0.95,
                     textstr,
                     transform=ax3.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            fig.tight_layout()
            if not pdf:
                plt.show()
            else:
                return fig

    def getAsymmetry1DPlots(self,
                            pdf=False,
                            isBinned=True,
                            nbin=50,
                            amount=5,
                            title="Histogram of Asymmetry of each Tray",
                            xmax=0.5,
                            xmin=-0.5):
        "Inputs:self-> sstring, pdf= False-> boolean, idBinned=True-> Boolean, nbin=50-> int, amount=5-> int, title='Histogram of Asymmetry of
        "of each Tray-> string, xmax=0.5->float, xmin=-0.5->float
        "Outputs: 4 1D hisstograms of the Asymmetry plots, one for each channel
        "Process: The code checks the value of isBinned, to see if either true or false, if true, the code returns a histogram showing the histogram
        " of the asymmetry of each tray. If the value is false then the second part of the code, hard-codes the dimensions of the histogram as well
        " as the mean, standard deviation and overflow"
        if isBinned:
            fig, axes = plt.subplots(nrows=4, ncols=1)
            plt.suptitle(title)
            ax0, ax1, ax2, ax3 = axes.flatten()
            # nbins = self.getBins(xmin, xmax, nbin)
            nbins = nbin
            ovflow = ((xmax < self.events_df['asymL1'].values) |
                      (self.events_df['asymL1'].values < xmin)).sum()
            ax0.hist(self.events_df['asymL1'],
                     range=(xmin, xmax),
                     bins=nbins,
                     histtype='step')
            s = self.events_df['asymL1']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax0.text(0.90,
                     0.95,
                     textstr,
                     transform=ax0.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ax0.set_xlim([xmin, xmax])
            ax0.set_title('Tray 1')
            ovflow = ((xmax < self.events_df['asymL2'].values) |
                      (self.events_df['asymL2'].values < xmin)).sum()
            ax1.hist(self.events_df['asymL2'],
                     range=(xmin, xmax),
                     bins=nbins,
                     histtype='step')
            ax1.set_xlim([xmin, xmax])
            ax1.set_title('Tray 2')
            s = self.events_df['asymL2']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax1.text(0.90,
                     0.95,
                     textstr,
                     transform=ax1.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ovflow = ((xmax < self.events_df['asymL3'].values) |
                      (self.events_df['asymL3'].values < xmin)).sum()
            ax2.hist(self.events_df['asymL3'],
                     range=(xmin, xmax),
                     bins=nbins,
                     histtype='step')
            ax2.set_xlim([xmin, xmax])
            ax2.set_title('Tray 3')
            s = self.events_df['asymL3']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax2.text(0.90,
                     0.95,
                     textstr,
                     transform=ax2.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ovflow = ((xmax < self.events_df['asymL4'].values) |
                      (self.events_df['asymL4'].values < xmin)).sum()
            ax3.hist(self.events_df['asymL4'],
                     range=(xmin, xmax),
                     bins=nbins,
                     histtype='step')
            ax3.set_xlim([xmin, xmax])
            ax3.set_title('Tray 4')
            s = self.events_df['asymL4']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax3.text(0.90,
                     0.95,
                     textstr,
                     transform=ax3.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            fig.tight_layout()
            if not pdf:
                plt.show()
            else:
                return fig
        else:
            fig, axes = plt.subplots(nrows=4, ncols=1)
            plt.suptitle("Histogram of Asymmetry of each Tray")
            ax0, ax1, ax2, ax3 = axes.flatten()
            xmin, xmax = -0.25, 0.25
            nbins = len(self.events_df['asymL1']) // amount
            ovflow = ((xmax < self.events_df['asymL1'].values) |
                      (self.events_df['asymL1'].values < xmin)).sum()
            ax0.hist(self.events_df['asymL1'], nbins, histtype='step')
            s = self.events_df['asymL1']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax0.text(0.90,
                     0.95,
                     textstr,
                     transform=ax0.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            ax0.set_xlim([xmin, xmax])
            ax0.set_title('Tray 1')
            nbins = len(self.events_df['asymL2']) // amount
            ovflow = ((xmax < self.events_df['asymL2'].values) |
                      (self.events_df['asymL2'].values < xmin)).sum()
            ax1.hist(self.events_df['asymL2'], nbins, histtype='step')
            ax1.set_xlim([xmin, xmax])
            ax1.set_title('Tray 2')
            s = self.events_df['asymL2']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax1.text(0.90,
                     0.95,
                     textstr,
                     transform=ax1.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            nbins = len(self.events_df['asymL3']) // amount
            ovflow = ((xmax < self.events_df['asymL3'].values) |
                      (self.events_df['asymL3'].values < xmin)).sum()
            ax2.hist(self.events_df['asymL3'], nbins, histtype='step')
            ax2.set_xlim([xmin, xmax])
            ax2.set_title('Tray 3')
            s = self.events_df['asymL3']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax2.text(0.90,
                     0.95,
                     textstr,
                     transform=ax2.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            nbins = len(self.events_df['asymL4']) // amount
            ovflow = ((xmax < self.events_df['asymL4'].values) |
                      (self.events_df['asymL4'].values < xmin)).sum()
            ax3.hist(self.events_df['asymL4'], nbins, histtype='step')
            ax3.set_xlim([xmin, xmax])
            ax3.set_title('Tray 4')
            s = self.events_df['asymL4']
            mean, std, count = s.describe().values[1], s.describe(
            ).values[2], s.describe().values[0]
            textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}\nBin: {}\nOverflow: {}".format(
                mean, std, count, nbin, ovflow)
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax3.text(0.90,
                     0.95,
                     textstr,
                     transform=ax3.transAxes,
                     fontsize=5,
                     verticalalignment='top',
                     bbox=props)
            fig.tight_layout()
            if not pdf:
                plt.show()
            else:
                return fig

    def getDataFrame(self, df):
        "Inputs: self-> string, df-> string "
        " Outputs: Muon Data Frame "
        " Process:This part of the code reads the code that comes before it and compiles the information to make 
        " a data frame. However this data frame doesn't have the ADC or TDC graphs."
        # return self.serialize_dataframe(df, self.newFileName)
        return parallelize_dataframe(df, self.completeDataFrameNoADCTDC,
                                     self.newFileName)

    def serialize_dataframe(self, df, path):
        " Inputs:self-> string, df-> string, path-> string "
        " Outputs:The complete data frame without the ADC or TDC graphs "
        " Process: the code takes the df variable and sets it equal to the self.completeDataFrameNoADCTDC(df) and saves the data frame and sends
        " it to the hdf dictionary
        df = self.completeDataFrameNoADCTDC(df)
        # feather.write_dataframe(df, path)
        df.to_hdf(path, key=path)
        return df

    def completeDataFrameNoADCTDC(self, df):
        "Inputs:self-> string, df-> string "
        " Outputs: The  pairing and storing of the variables to a number"
        " Process: The code takes the values of the L's and R's from a list and pairs them together. The second part of the code calculates 
        " the angle at which the muon hit came from, then stores this information  
        df['L1'] = self.getTDC(df['TDC'].to_numpy(), 0)
        df['R1'] = self.getTDC(df['TDC'].values, 1)
        df['L2'] = self.getTDC(df['TDC'].values, 2)
        df['R2'] = self.getTDC(df['TDC'].values, 3)
        df['L3'] = self.getTDC(df['TDC'].values, 6)
        df['R3'] = self.getTDC(df['TDC'].values, 7)
        df['L4'] = self.getTDC(df['TDC'].values, 8)
        df['R4'] = self.getTDC(df['TDC'].values, 9)
        df['ADC0'] = self.getADC(df['ADC'].values, 0)
        df['ADC1'] = self.getADC(df['ADC'].values, 1)
        df['ADC2'] = self.getADC(df['ADC'].values, 2)
        df['ADC3'] = self.getADC(df['ADC'].values, 3)
        df['ADC4'] = self.getADC(df['ADC'].values, 4)
        df['ADC5'] = self.getADC(df['ADC'].values, 5)
        df['ADC6'] = self.getADC(df['ADC'].values, 6)
        df['ADC7'] = self.getADC(df['ADC'].values, 7)
        df['ADC8'] = self.getADC(df['ADC'].values, 8)
        df['ADC9'] = self.getADC(df['ADC'].values, 9)
        df['ADC10'] = self.getADC(df['ADC'].values, 10)
        df['ADC11'] = self.getADC(df['ADC'].values, 11)
        df['TopCounter'] = self.getTDC(df['TDC'].values, 4)
        df['BottomCounter'] = self.getTDC(df['TDC'].values, 10)
        df['sumL1'] = df.eval('L1 + R1')
        df['sumL2'] = df.eval('L2 + R2')
        df['sumL3'] = df.eval('L3 + R3')
        df['sumL4'] = df.eval('L4 + R4')
        df['diffL1'] = df.eval('L1 - R1')
        df['diffL2'] = df.eval('L2 - R2')
        df['diffL3'] = df.eval('L3 - R3')
        df['diffL4'] = df.eval('L4 - R4')
        df['asymL1'] = df.eval('diffL1 / sumL1')
        df['asymL2'] = df.eval('diffL2 / sumL2')
        df['asymL3'] = df.eval('diffL3 / sumL3')
        df['asymL4'] = df.eval('diffL4 / sumL4')
        df["numLHit"] = df.eval(
            'l1hit + l2hit + l3hit + l4hit + r1hit + r2hit + r3hit + r4hit')
        df['theta_x1'] = df.eval("asymL2/asymL1") * (180 / np.pi)
        df['theta_y1'] = df.eval("asymL1/asymL2") * (180 / np.pi)
        df['theta_x2'] = df.eval("asymL4/asymL3") * (180 / np.pi)
        df['theta_y2'] = df.eval("asymL3/asymL4") * (180 / np.pi)
        # process Z
        asymT1 = df['asymL1'].values
        asymT2 = df['asymL2'].values
        asymT3 = df['asymL3'].values
        asymT4 = df['asymL4'].values
        zangles = np.arctan(
            np.sqrt((asymT1 - asymT3)**2 +
                    (asymT2 - asymT4)**2) / self.d_asym) * (180 / np.pi)
        df["z_angle"] = zangles
        df['SmallCounter'] = self.getTDC(df['TDC'].values, 12)
        # calculate speed
        toSeconds = 0.000000001
        tdcToNs = 0.5  #ns
        c = 299792458  #m/s
        angles = np.array(np.cos(zangles * (np.pi / 180)))
        d_mu = self.d_phys / angles  # m
        t1 = df["L1"] * tdcToNs
        t2 = df["L3"] * tdcToNs
        del_t = (t1 - t2) * toSeconds
        speeds = (abs(d_mu / del_t)) / c
        df["speed"] = speeds
        return df

    def completeDataFrame(self, df):
        "Inputs: self-> string, df-> string "
        " Outputs: All the variables have an assigned number and graph "
        "Process: takes the different variable names and assigns them values from a list. The sum variables are obtained from performing arithmetic
        " operations of the L and R variables, same for the diff variables. The asym values come from the division of the diff and sum variables.
        "The code then returns the z angles and calculates the time difference between hits, to the nanosecond."
        
        df['L1'] = self.getTDC(df['TDC'].to_numpy(), 0)
        df['R1'] = self.getTDC(df['TDC'].values, 1)
        df['L2'] = self.getTDC(df['TDC'].values, 2)
        df['R2'] = self.getTDC(df['TDC'].values, 3)
        df['L3'] = self.getTDC(df['TDC'].values, 6)
        df['R3'] = self.getTDC(df['TDC'].values, 7)
        df['L4'] = self.getTDC(df['TDC'].values, 8)
        df['R4'] = self.getTDC(df['TDC'].values, 9)
        df['ADC0'] = self.getADC(df['ADC'].values, 0)
        df['ADC1'] = self.getADC(df['ADC'].values, 1)
        df['ADC2'] = self.getADC(df['ADC'].values, 2)
        df['ADC3'] = self.getADC(df['ADC'].values, 3)
        df['ADC4'] = self.getADC(df['ADC'].values, 4)
        df['ADC5'] = self.getADC(df['ADC'].values, 5)
        df['ADC6'] = self.getADC(df['ADC'].values, 6)
        df['ADC7'] = self.getADC(df['ADC'].values, 7)
        df['ADC8'] = self.getADC(df['ADC'].values, 8)
        df['ADC9'] = self.getADC(df['ADC'].values, 9)
        df['ADC10'] = self.getADC(df['ADC'].values, 10)
        df['ADC11'] = self.getADC(df['ADC'].values, 11)
        df['TopCounter'] = self.getTDC(df['TDC'].values, 4)
        df['BottomCounter'] = self.getTDC(df['TDC'].values, 10)
        df['sumL1'] = df.eval('L1 + R1')
        df['sumL2'] = df.eval('L2 + R2')
        df['sumL3'] = df.eval('L3 + R3')
        df['sumL4'] = df.eval('L4 + R4')
        df['diffL1'] = df.eval('L1 - R1')
        df['diffL2'] = df.eval('L2 - R2')
        df['diffL3'] = df.eval('L3 - R3')
        df['diffL4'] = df.eval('L4 - R4')
        df['asymL1'] = df.eval('diffL1 / sumL1')
        df['asymL2'] = df.eval('diffL2 / sumL2')
        df['asymL3'] = df.eval('diffL3 / sumL3')
        df['asymL4'] = df.eval('diffL4 / sumL4')
        df['theta_x1'] = self.events_df.eval("asymL2/asymL1") * (180 / np.pi)
        df['theta_y1'] = self.events_df.eval("asymL1/asymL2") * (180 / np.pi)
        df['theta_x2'] = self.events_df.eval("asymL4/asymL3") * (180 / np.pi)
        df['theta_y2'] = self.events_df.eval("asymL3/asymL4") * (180 / np.pi)
        df["numLHit"] = df.eval(
            'l1hit + l2hit + l3hit + l4hit + r1hit + r2hit + r3hit + r4hit')
        # process Z
        asymT1 = df['asymL1'].values
        asymT2 = df['asymL2'].values
        asymT3 = df['asymL3'].values
        asymT4 = df['asymL4'].values
        zangles = np.arctan(
            np.sqrt((asymT1 - asymT3)**2 +
                    (asymT2 - asymT4)**2) / self.d_asym) * (180 / np.pi)
        df["z_angle"] = zangles
        df['SmallCounter'] = self.getTDC(df['TDC'].values, 12)
        # calculate speed
        toSeconds = 0.000000001
        tdcToNs = 0.5  #ns
        c = 299792458  #m/s
        angles = np.array(np.cos(zangles * (np.pi / 180)))
        d_mu = self.d_phys / angles  # m
        t1 = df["L1"] * tdcToNs
        t2 = df["L3"] * tdcToNs
        del_t = (t1 - t2) * toSeconds
        speeds = (abs(d_mu / del_t)) / c
        df["speed"] = speeds
        return df

    def getMultiTDCEventsHisto(self):
        "inputs:self-> string"
        "Outputs: A histogram  "
        " Process:The code reads the x dictionary and looks at each element in the dictionary, and if the length of j is greater than 2, it adds
        " j to the list of y."
        x = self.get("TDC")
        y = []
        for i in x:
            for j in i:
                if len(j) > 2:
                    y.append(j)
        plt.hist(y)
        plt.title("Number of Events with Multiple TDCs")
        plt.title("Number of TDC / event")
        plt.show()

    def getADC(self, event, chNum):
        "Inputs:self-> string, event-> string, chNum-> string "
        "Outputs: adcs "
        "Process: adds chNum to the adcs list ans returns the adcs list "
        adcs = []
        for ev in event:
            adcs.append(ev[chNum])
        return adcs

    def getTDC(self, event, chNum):
        "Inputs: self-> string, event-> string, chNum-> string"
        "Outputs:tdcs "
        "Process:Makes a list called tdcs and sets the variable tdc equal to 0, then checks to see if the ev equals to none, and if it does not,
        "the code adds the first number from the tdcs list to the tdcVals. If the ev does equal to none, then the code sets the variable tdc to
        " none and adds the variable tdc to the tdcs list"
        tdcs = []
        for ev in event:
            tdc = 0
            tdcVals = []
            if ev != None:
                for i in ev:
                    if chNum in i:
                        tdcVals.append(i[1])
                tdc = self.getCorrectTDC(tdcVals)
            else:
                tdc = None
            tdcs.append(tdc)
        return tdcs

    def removeMultiHits(self, event):
        "Inputs:self-> string, event-> string "
        "Outputs: counts "
        "Ptocess: This code makes a list called counts the code adds numbers to the list by checking to see if the ev nuber equals to none,
        " and if it does not, the code then adds the length of the list of t that comes from the itertools.groupby dictionary. If ev does 
        "equal none, then the code adds 0 to the counts list"
        counts = []
        for ev in event:
            if ev != None:
                counts.append(
                    len([
                        next(t)
                        for _, t in itertools.groupby(ev, lambda x: x[0])
                    ]))
            else:
                counts.append(0)
        return counts

    def get(self, term):
        "Inputs:self-> string, term-> string "
        "Outputs:events "
        "Process: the code retutns events "
        return self.events_df[term].values

    def getCorrectTDC(self, tdcs):
        "Inputs:self->string, tdcs-> string "
        " Outputs: max tdcs "
        "Process: if the length of tdcs is 1, return the number, if the length is equal to 0 return none, if the the length equals to the last,
        " it gives back tdcs[-1], otherwise it returns tdcs[0] for the first number, or min or max tdcs for the max or min number.
        if len(tdcs) == 1:
            return tdcs[0]
        elif len(tdcs) == 0:
            return None
        else:
            if self.d1 == "last":
                # print("len(tdcs) : {}".format(len(tdcs)))
                return tdcs[-1]
            elif self.d1 == "first":
                return tdcs[0]
            elif self.d1 == "min":
                return min(tdcs)
            elif self.d1 == "max":
                return max(tdcs)

    def show(self):
        "Inputs:self->string "
        "Outputs: events "
        "Process:returns the number of events "
        return self.events_df
        # print(self.events_df)

    def lookAt(self, query_term):
        "Inputs:self-> string, query_term->string "
        "Outputs: the events in question: "
        "Process: give the events that are under speculation"
        return self.events_df[query_term]
        # print(self.events_df[query_term])

    def removeNoTDCEvents(self):
        "Innputs:self->string"
        "Outputs: the number of events with their tdc values "
        "Process: the code gives back the list "
        self.events_df = self.events_df[~self.events_df["TDC"].isnull()]

    def summary(self):
        "Inputs: self->string"
        "Outputs: events "
        "Process: the code gives back the events that were in the info dictionary"
        return self.events_df.info()
        # print(self.events_df.info())

    def generateMultipleTDCHitData(self):
        "Inputs: self->string"
        "Outputs: the events with their tdc values "
        "Process: makes a list of tdc hits and tdc events snd for each event in the num_tdc_read, if the event equals none, then the code does
        "nothing, but if the event equals something the code adds the event list to the tdc events list and adds teh tdc list to the tdc hits list
        criteria = self.d1
        num_tdc_read = self.events_df["TDC"].values
        tdc_hits = []
        tdc_event = []
        for event in num_tdc_read:
            if event == None:
                tdc_hits.append([0, 0, 0, 0])
                tdc_event.append(None)
            else:
                tdc_list, ev_list = self.calculateTDCHits(event, criteria)
                tdc_event.append(ev_list)
                tdc_hits.append(tdc_list)
        self.events_df["TDC_hit_num"] = tdc_hits
        self.events_df["TDC_Ana"] = tdc_event
        # self.generateNumChannelsReadData()
        # self.generateTDCAnalyzedData()

    def createTDCValues(self, tdc_hits, event, criteria):
        "Inputs: self-> string, tdc_hits->string, event->string, criteria->string"
        "Outputs: tdc values"
        "Prrocess: if the criteia is equal to last, list the items, if the criteria is first, remove the event, if the criteria is max, remove the
        "number, if the number is min, add that number to the list, once that is done, for every name in the list add a number.
        if criteria == "last":
            ev = list(OrderedDict(event).items())
        elif criteria == "first":
            ev = remove_if_first_index(event)
        elif criteria == "max":
            ev = list(dict(list(event), key=lambda v: int(v[1])).items())
            ev.pop()
        elif criteria == "min":
            d = defaultdict(list)
            for name, num in event:
                d[name].append(num)
            ev = list(zip(d, map(min, d.values())))
        return ev

    def calculateTDCHits(self, event, criteria):
        "Inputs:self->string, event->string, criteria->string "
        "Outputs: the tdc list snd the events they go with "
        " Process: for every element in the tdc list, the code sees what the value is, if the value is 0,1,3, or 4, it performs the operation 
        "c=c+1, and records the numbers in the tdc hit list and returns the tdc list with the event it goes with
        zero_c = 0
        one_c = 0
        three_c = 0
        four_c = 0
        tdc_event = []
        for i in event:
            if i[0] == 0:
                zero_c += 1
            elif i[0] == 1:
                one_c += 1
            elif i[0] == 3:
                three_c += 1
            elif i[0] == 4:
                four_c += 1
        tdc_hit = [zero_c, one_c, three_c, four_c]
        ev = self.createTDCValues(tdc_hit, event, criteria)
        return tdc_hit, ev

    def getHisto1DInfo(self, queryName):
        "Innputs:self->string, queryName->string "
        "Outputs: mean, std, and count"
        "Process: looks at the number of events and calculates the mean, std, and count "
        s = self.events_df[queryName]
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        return mean, std, count

    def getHistogram(self,
                     queryName,
                     title="",
                     nbins=200,
                     pdf=False,
                     range=None):
        "Inputs: self->string, queryName->string, title-> string, nbins=200-> int, pdf= false-> boolean, range=none-> string "
        "Outputs: plots a histogram "
        "Process: the code tskes the events list and plots the points in a histogram "
        s = self.events_df[queryName]
        # plt.figure(figsize=(3, 3))
        ax = s.plot.hist(alpha=0.7, bins=nbins, range=range)
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}".format(
            mean, std, count)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.7)
        ax.text(0.80,
                0.95,
                textstr,
                transform=ax.transAxes,
                fontsize=12,
                verticalalignment='top',
                bbox=props)
        ax.set_title("Histogram of {} {}".format(queryName, title))
        if not pdf:
            plt.show()
        else:
            return ax

    def getKDE(self, queryName, bw_method=None, nbins=200, range=None):
        "Inputs: self->string, queryName->string, bw_method=none-> string, nbins=200-> int, range=none-> string "
        "Outputs: plots the  kernel density estimation  "
        "Process: plots the kde by using the events dataframe query list and displays the mean, std, and count "
        s = self.events_df[queryName].to_numpy()
        s = pd.Series(s)
        ax = s.plot.kde(bw_method=bw_method, bins=nbins, range=range)
        mean, std, count = s.describe().values[1], s.describe(
        ).values[2], s.describe().values[0]
        textstr = "Mean: {:0.3f}\nStd: {:0.3f}\nCount: {}".format(
            mean, std, count)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.80,
                0.95,
                textstr,
                transform=ax.transAxes,
                fontsize=14,
                verticalalignment='top',
                bbox=props)
        ax.set_title("Probability Density of {}".format(queryName))
        plt.show()

    def getFilteredHistogram(self, queryName, filter, nbins=200, title=""):
        "Inputs:self->string, queryName-> string, filter->string, nbins=200->int, title=-> string
        "outputs: Histogram"
        "Process: takes the events dataframe and sends the frame through a filter and plots the results in a histogram "
        self.events_df.hist(column=queryName, bins=nbins, by=filter)
        plt.suptitle("Histograms of {} grouped by {} {}".format(
            queryName, filter, title))
        plt.ylabel("Frequency")
        plt.show()

    def getComparableHistogram(self, queries, nbins=200, title="", lims=None):
        "Inputs:self->string, queries->string, nbins=200->int, title=""->string, lims=None->string "
        "Outputs: histogram "
        "Process: plots a histogram "
        s = pd.DataFrame(columns=queries)
        s = s.fillna(0)  # with 0s rather than NaNs
        for query in queries:
            s[query] = self.events_df[query]
        ax = s.plot.hist(alpha=0.6, bins=nbins, range=lims)
        plt.title("Histogram of {} {}".format(str(queries), title))
        plt.show()

    def get2DHistogram(self,
                       xvals,
                       yvals,
                       title,
                       xlabel,
                       ylabel,
                       xmin,
                       xmax,
                       ymin,
                       ymax,
                       nbins=150,
                       pdf=False,
                       zLog=True):
        "Inputs:self-> string, xvals->string, yvals->string, title-> string, xlabel->string, ylabel-> string, xmin-> string, xmax->string, 
        "ymin-> string, ymax->string, nbins=150-> int, pdf=false-> boolean, zlog=true-> boolean
        "Outputs: a 2d histogram "
        "Process: plots a histogram"
        name = title.replace(" ", "") + "_run_" + self.runNum
        self.pdfList.append(name)
        if not pdf:
            Histo2D(name,
                    title,
                    xlabel,
                    nbins,
                    xmin,
                    xmax,
                    xvals,
                    ylabel,
                    nbins,
                    ymin,
                    ymax,
                    yvals,
                    pdf,
                    zIsLog=zLog)
        else:
            return Histo2D(name,
                           title,
                           xlabel,
                           nbins,
                           xmin,
                           xmax,
                           xvals,
                           ylabel,
                           nbins,
                           ymin,
                           ymax,
                           yvals,
                           pdf,
                           zIsLog=zLog)

    def getFilteredEvents(self, conditions):
        df = self.events_df
        numConditions = len(conditions)
        if numConditions == 1:
            return conditionParser_single(self.events_df, conditions)
        else:
            df1 = conditionParser_multiple(self.events_df, conditions[0])
            df2 = conditionParser_multiple(self.events_df, conditions[1])
            main_op = conditions[2]
            if main_op == "&":
                intersection = df1[['event_num'
                                    ]].merge(df2[['event_num'
                                                  ]]).drop_duplicates()
                res = pd.concat(
                    [df1.merge(intersection),
                     df2.merge(intersection)])
                # print(res)
            else:
                res = pd.concat([df1, df2])
                # print(res)
            return res

    def dropna(arr, *args, **kwarg):
        assert isinstance(arr, np.ndarray)
        dropped = pd.DataFrame(arr).dropna(*args, **kwarg).values
        if arr.ndim == 1:
            dropped = dropped.flatten()
        return dropped

    def getFilteredPlot(self, term, value, cond, title="", reload=True):
        self.keepEvents(term, value, cond)
        self.getPlot(term, title=title)
        if reload:
            self.reload()

    @dispatch(str)
    def getPlot(self, query):
        "Input:self->string, query->string "
        "Outputs: Histogram: "
        "Process:pulls the data from the dataframe and plots the information with the axes labeled and a title "
        self.events_df[query].plot()
        plt.xlabel("Event Number")
        plt.ylabel(str(query))
        plt.title("Plot of {} event series ".format(query))
        plt.show()

    @dispatch(list)
    def getPlot(self, queries, title=""):
        "Inputs: self->string, queries->string, title=""->string"
        "Outputs: a line plot "
        "Process: takes eventsl from the data frame and looks at the first 2 columns and plots them with a title "
        plt.plot(self.events_df[queries[0]].values,
                 self.events_df[queries[1]].values)
        plt.xlabel(str(queries[0]))
        plt.ylabel(str(queries[1]))
        plt.title("Line Plot of {} against {} {}".format(
            queries[0], queries[1], title))
        plt.show()

    def getScatterPlot(self, queries, title=""):
        "Inputs:self->string, queries->string, title=""->string "
        "Outputs:scatterplot "
        "Process:the code looks at the dataframe and pulls the firsst 2 columns and plots the data in a scatterplot "
        plt.scatter(self.events_df[queries[0]].values,
                    self.events_df[queries[1]].values)
        plt.xlabel(str(queries[0]))
        plt.ylabel(str(queries[1]))
        plt.title("Scatter Plot of {} against {} {}".format(
            queries[0], queries[1], title))
        plt.show()

    def get3DScatterPlot(self, queries, title="", xlims=None, ylims=None):
        "Inputs:self->string, queries->string, title=""->string, xlims=None->string, ylims=None->string "
        "Outputs: a 3d scatterplot "
        "process: looks at the data frame, pulls the first 3 columns and plots that data into a 3d scatteplot "
        self.events_df.plot.scatter(x=queries[0],
                                    y=queries[1],
                                    c=queries[2],
                                    colormap='viridis')
        plt.xlim(xlims)
        plt.ylim(ylims)
        plt.title(title)
        plt.show()

    def getEventInfo(self, eventNum):
        "Inputs: self->string, eventNum->string"
        "Outputs: the data frame  "
        "Process: looks at the event number column in the data frame and looks to see if those numbers are equal wih the variable eventNum, if so
        " nothing happens, if not, im not sure
        if isinstance(eventNum, int):
            df = self.events_df.loc[self.events_df["event_num"] == eventNum]
        elif isinstance(eventNum, list):
            df = self.events_df[self.events_df['event_num'].between(
                eventNum[0], eventNum[1])]
        return df
        # print(df)

    def getStats(self, queryName):
        "Inputs:self->string, queryName ->string"
        "Outputs: the stats of the data frame, the mean, std, counts, and overflow"
        "Process: this code takes the stats of the whole data frame"
        s = self.events_df[queryName]
        return s.describe()
        # print(s.describe())

    def removeOutliers(self):
        "Inputs: self->string"
        "Outputs: the outliers are taken out of the data "
        " Process:this code places limits on the acceptable data limits and removes those points of data that do not fall in that range "
        for queryName in self.quant_query_terms:
            q_low = self.events_df[queryName].quantile(0.01)
            q_hi = self.events_df[queryName].quantile(0.99)
            self.events_df = self.events_df[
                (self.events_df[queryName] < q_hi)
                & (self.events_df[queryName] > q_low)]

    def keepEvents(self, term, value, cond):
        "inputs: self->string, term->string, value->string, cond->string"
        "Outputs: acceptable values  "
        "Process: this part of the code looks at the numbers and data in the dataframe, and displays  "
        if cond == "<":
            self.events_df = self.events_df[self.events_df[term] < value]
        elif cond == ">":
            self.events_df = self.events_df[self.events_df[term] > value]
        elif cond == "==":
            self.events_df = self.events_df[self.events_df[term] == value]
        elif cond == ">=":
            self.events_df = self.events_df[self.events_df[term] >= value]
        elif cond == "<=":
            self.events_df = self.events_df[self.events_df[term] <= value]
        elif cond == "!=":
            self.events_df = self.events_df[self.events_df[term] != value]

    # @staticmethod

    def keepEventsWithinStdDev(self, queryName, numStd):
        "Inputs:self->string, queryName->string, numStd->string "
        "Outputs:numbers and data that fall in the first std "
        "Process: compares the data with the limit of the first std, and for those outside of that, they are not put in the graph "
        df_filtered = scrubbedDataFrame(self.events_df, queryName, numStd)
        self.events_df = df_filtered

    def getTrimmedHistogram(self, queryName, numStd, nbins=200):
        "Inputs:self->string, queryName->string, numStd->string, nbins=200->int "
        "Outputs:a filtered histogram "
        "Process: the code pulls the filtered data frame and puts those points into a histogram "
        df_filtered = scrubbedDataFrame(self.events_df, queryName, numStd)
        getHistogram(df_filtered,
                     queryName,
                     title="(Events within {} std dev)".format(numStd),
                     nbins=nbins)

    def getTrimmed2DHistogram(df, queryName, numStd, nbins=200):
        "Inouts:df->string, queryName->string, numStd->string, nbins=200->int "
        "Outputs: a filtered 2d histogram "
        "Process: plots a filtered 2d histogram "
        pass

    def getTrimmedFilteredHistogram(self, queryName, numStd, nbins=200):
        "Inputs: self, queryName, numStd, nbins=200
        "Outputs: a filtered Histogram 
        " Process: pulls the filtered data and plots it as a histogram
        df_filtered = scrubbedDataFrame(self.events_df, queryName, numStd)
        getFilteredHistogram(df_filtered,
                             queryName,
                             nbins,
                             title="(Events within {} std dev)".format(numStd))

    def getTrimmedComparableHistogram(self, queries, numStd, nbins=200):
        "Inputs: self, queries, numStd, nbins=200
        "Output: Histogram with the number of events within the standard deviation 
        "Process: takung columns and filling the empty spaces with zeros and useing that to make an array. 
        "With that array, it's forming a histogram with the events within the standard deviation
        s = pd.DataFrame(columns=queries)
        s = s.fillna(0)  # with 0s rather than NaNs
        for query in queries:
            s[query] = scrubbedDataFrame(self.events_df, query, numStd)[query]
        ax = s.plot.hist(alpha=0.7, bins=nbins, histtype='step')
        plt.title("Histogram of {} (Events within {} std dev)".format(
            str(queries), numStd))
        plt.show()
