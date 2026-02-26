from django.core.management import BaseCommand, CommandError
from django.conf import settings

from rest_framework.response import Response
import os
import math
import json
import ast 

from datetime import date, datetime, timedelta
import geopandas as gpd
import pandas as pd
import xarray as xr
import rioxarray
import shapely
import netCDF4
import numpy as np
from pyidw import idw
import rasterio

from datetime import date, datetime, timedelta


from data_load.models import MonsoonBasinWiseFlashFloodForecast


stationDict={ 
    1:'khaliajhuri', 
    2:'gowainghat', 
    3:'dharmapasha',
    4:'userbasin',
    5:'laurergarh',
    6:'muslimpur',
    7:'debidwar',
    8:'ballah',
    9:'habiganj',
    10:'parshuram',
    11:'cumilla',
    12:'nakuagaon'
    }

stationThresholds = {
    1: {24: 96.89950599, 48: 162.8320331, 72: 220.5977546, 120: 323.3900146, 168: 416.0549444, 240: 543.4315997},  # khaliajhuri
    2: {24: 62.91949742, 48: 92.91302073, 72: 116.7093532, 120: 155.5491175, 168: 187.9516346, 240: 229.6988847},  # gowainghat
    3: {24: 24.5, 48: 41.5, 72: 56.5, 120: 83, 168: 107.5, 240: 141},  # dharmapasha (unchanged)
    4: {24: 25, 48: 40.5, 72: 53.5, 120: 76, 168: 96, 240: 123},  # userbasin (unchanged)
    5: {24: 52.66627048, 48: 65.83191795, 72: 75.01043443, 120: 88.41715826, 168: 98.53177944, 240: 110.5199031},  # laurergarh
    6: {24: 33.50, 48: 51.84, 72: 66.93, 120: 92.34, 168: 114.14, 240: 142.90},  # muslimpur (unchanged)
    7: {24: 41.37244531, 48: 59.10820306, 72: 72.82489007, 120: 94.72459479, 168: 112.6349373, 240: 135.331633},  # debidwar
    8: {24: 28.77247366, 48: 35.77137016, 72: 40.63017364, 120: 47.70181973, 168: 53.01955989, 240: 59.30527458},  # ballah
    9: {24: 14, 48: 22, 72: 30, 120: 44, 168: 56, 240: 73},  # habiganj (unchanged)
    10: {24: 48.53562859, 48: 67.45165462, 72: 81.77158915, 120: 104.2169518, 168: 122.2704102, 240: 144.8339302},  # parshuram
    11: {24: 9.732483938, 48: 28.22773042, 72: 52.62513159, 120: 115.3465484, 168: 193.4155288, 240: 334.5467914},  # cumilla
    12: {24: 30.52, 48: 40.468, 72: 47.73, 120: 58.75, 168: 67.37, 240: 77.89}  # nakuagaon (unchanged)
}

stationThresholdsList = {
    1: {0: [24, 96.89950599], 1: [48, 162.8320331], 2: [72, 220.5977546], 3: [120, 323.3900146], 4: [168, 416.0549444], 5: [240, 543.4315997]},  # khaliajhuri
    2: {0: [24, 62.91949742], 1: [48, 92.91302073], 2: [72, 116.7093532], 3: [120, 155.5491175], 4: [168, 187.9516346], 5: [240, 229.6988847]},  # gowainghat
    3: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83], 4: [168, 107.5], 5: [240, 141]},  # dharmapasha (unchanged)
    4: {0: [24, 25], 1: [48, 40.5], 2: [72, 53.5], 3: [120, 76], 4: [168, 96], 5: [240, 123]},  # userbasin (unchanged)
    5: {0: [24, 52.66627048], 1: [48, 65.83191795], 2: [72, 75.01043443], 3: [120, 88.41715826], 4: [168, 98.53177944], 5: [240, 110.5199031]},  # laurergarh
    6: {0: [24, 33.50], 1: [48, 51.84], 2: [72, 66.93], 3: [120, 92.34], 4: [168, 114.14], 5: [240, 142.90]},  # muslimpur (unchanged)
    7: {0: [24, 41.37244531], 1: [48, 59.10820306], 2: [72, 72.82489007], 3: [120, 94.72459479], 4: [168, 112.6349373], 5: [240, 135.331633]},  # debidwar
    8: {0: [24, 28.77247366], 1: [48, 35.77137016], 2: [72, 40.63017364], 3: [120, 47.70181973], 4: [168, 53.01955989], 5: [240, 59.30527458]},  # ballah
    9: {0: [24, 14], 1: [48, 22], 2: [72, 30], 3: [120, 44], 4: [168, 56], 5: [240, 73]},  # habiganj (unchanged)
    10: {0: [24, 48.53562859], 1: [48, 67.45165462], 2: [72, 81.77158915], 3: [120, 104.2169518], 4: [168, 122.2704102], 5: [240, 144.8339302]},  # parshuram
    11: {0: [24, 9.732483938], 1: [48, 28.22773042], 2: [72, 52.62513159], 3: [120, 115.3465484], 4: [168, 193.4155288], 5: [240, 334.5467914]},  # cumilla
    12: {0: [24, 30.52], 1: [48, 40.46], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]}  # nakuagaon (unchanged)
}




class Command(BaseCommand):

    help='Generate Basin Wise Flashflood for Presentday'

    # def add_arguments(self,parser):
    #     parser.add_argument('date',type=str, help='date for generating Rainfall Distribution Map')

        
    def handle(self, *args, **kwargs):
        
        try :
            dateInput = kwargs['date']
            # print('Date Input Form Parameter', dateInput)

        except:
            updateDate=datetime.today()-timedelta(days=0)
            dateInput=datetime.strftime(updateDate,'%Y-%m-%d')
            # print('Date Input Without Parameter : ', dateInput)

        self.main(dateInput)  

    def generateDownloadFileNameList(self,downloadYear,givenDate):
        
        fileNameList=[]
        
        datetimeGivenDate = datetime.strptime(givenDate,"%Y-%m-%d")
        # print('Given Date in Download File Name List: ', datetimeGivenDate.timetuple().tm_yday)

        # dayOfTheYear=datetime.now().timetuple().tm_yday
        dayOfTheYear = datetimeGivenDate.timetuple().tm_yday

        # print('Timetuple : ',datetime.now().timetuple())

        today=datetime.now()
        todayDateString=today.strftime("%Y-%m-%d")
        # print('Date Today: ', todayDateString, 'Day of the Year: ', dayOfTheYear)

        for i in range(1,11):
            
            downloadDay=dayOfTheYear-i
            numberOfDigits = int(math.log10(downloadDay))+1
            if numberOfDigits==2:downloadDay = str(downloadDay).rjust(3, '0')
            else: downloadDay = str(downloadDay)
            dowanloadFileName=str(downloadYear)+downloadDay+'.nc'

            fileNameList.append(dowanloadFileName)
        
        return fileNameList

    def generateObservedDataframe(self,dailyPrecipitationDict):


        dateList=list(dailyPrecipitationDict.keys())
        rainfallList=list(dailyPrecipitationDict.values())
        dailyRainfallDict={'Date':dateList,'Rainfall':rainfallList}
        observedRainfallDF=pd.DataFrame.from_dict(dailyRainfallDict,orient='columns')
        observedRainfallDF.sort_values(by='Date',inplace=True)
        observedRainfallDF.reset_index(drop=True,inplace=True)

        return observedRainfallDF

    def computeBasinWiseForecast(self, stationName,givenDate):

        dir_path = os.getcwd()

        basin_json_file_path=os.path.join(dir_path,f'assets/floodForecastStations/{stationName}.json')
        stationGDF=gpd.read_file(basin_json_file_path,crs="epsg:4326")



        # print('Given Forecast Date: ', givenDate, 'For station: ', stationName)

        dateString = givenDate[8:10]+givenDate[5:7]+givenDate[:4]

        fileName=dateString+'.nc'

        if stationName !='cambodia':
            forecast_file_path = os.path.join(dir_path,f'forecast/{fileName}')
        elif stationName =='cambodia':
            print('In cambodia Forecast ....')
            forecast_file_path = os.path.join(dir_path,f'cambodiaForecast/{fileName}')


        fileExist = os.path.isfile(forecast_file_path)

        if fileExist: 
            # print('File Exists : ', fileExist)
            pass
        else:
            # print('Forecast File Does Not Exist ')
            previousDate = datetime.strptime(givenDate,'%Y-%m-%d') 
            previousDate = previousDate - timedelta(days=1)
            previousDate = datetime.strftime(previousDate,'%Y-%m-%d')

            dateString = previousDate[8:10]+previousDate[5:7]+previousDate[:4]

            fileName=dateString+'.nc'

            if stationName !='cambodia':
                forecast_file_path = os.path.join(dir_path,f'forecast/{fileName}')
            elif stationName =='cambodia':
                print('In cambodia Forecast ....')
                forecast_file_path = os.path.join(dir_path,f'cambodiaForecast/{fileName}')

        forecastDataset=xr.open_dataset(forecast_file_path)

        # print('Forecast Dataset File Path: ', forecast_file_path)
        # print(forecastDataset)

        forecastDataset.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True)
        forecastDataset.rio.write_crs("epsg:4326", inplace=True)
        clippedForecast = forecastDataset.rio.clip(stationGDF.geometry, stationGDF.crs, drop=True)

        # print(clippedForecast)



        dateList=list(clippedForecast.indexes['time'].strftime('%Y-%m-%d %H:%M:%S'))
        # dateList=list(dailyForecast.indexes['time'].strftime('%Y-%m-%d'))

        forecastPrecipitationDict={}
        dateIndex=0

        for day in range(0,len(dateList),4):
            totalPrecipitation=0
            # thisDay=dateList[dateIndex]
            thisDay=dateList[day]

            # print(thisDay)
            oneDayData=clippedForecast.sel(time=thisDay)
            # oneDayData=clippedForecast.sel(time=thisDay[:11])

            weights = np.cos(np.deg2rad(oneDayData.latitude))
            weights.name = "weights"
            rainfall_weighted = oneDayData.weighted(weights)
            weighted_mean = oneDayData.mean(("longitude", "latitude"))
            
            meancpValue=weighted_mean['cp'].values.tolist()
            meanlspValue=weighted_mean['lsp'].values.tolist()

            # totalPrecipitation= np.nansum(meancpValue)+np.nansum(meanlspValue)

            totalPrecipitation= meancpValue+meanlspValue
            if math.isnan(totalPrecipitation):totalPrecipitation=0.00

            forecastPrecipitationDict[dateList[dateIndex]]=totalPrecipitation*1000
            dateIndex=dateIndex+4

        rainfallValues=list(forecastPrecipitationDict.values())
        dateValues=list(forecastPrecipitationDict.keys())
        dateValues=[date[:-9] for date in dateValues]

        dailyRainfallValue=[]
        for i in range(8):
            rainfallAmount=round((rainfallValues[i+1]-rainfallValues[i]),4)
            dailyRainfallValue.append(rainfallAmount)

        forecastPrecipitationDict=dict(zip(dateValues,dailyRainfallValue))

        return forecastPrecipitationDict

    def generateForecastDataframe(self,forecastPrecipitationDict):

        dateList=list(forecastPrecipitationDict.keys())
        rainfallList=list(forecastPrecipitationDict.values())
        dailyRainfallDict={'Date':dateList,'Rainfall':rainfallList}
        forecastRainfallDF=pd.DataFrame.from_dict(dailyRainfallDict,orient='columns')
        forecastRainfallDF.sort_values(by='Date',inplace=True)
        forecastRainfallDF.reset_index(drop=True,inplace=True)

        return forecastRainfallDF

    def returnDesiredDataframe(self,observedRainfallDF,forecastRainfallDF):
        requiredDF=pd.concat([observedRainfallDF,forecastRainfallDF])
        requiredDF.reset_index(drop=True,inplace=True)

        return requiredDF


    def computeDailyBasinWiseMeanPrecipitation(self,fileName,stationName,dailyPrecipitationDict):
        
        stationGDF=gpd.read_file(f'assets/floodForecastStations/{stationName}.json',crs="epsg:4326")
        # print('Station Dataframe: \n', stationGDF)
        dataset=xr.open_dataset(f"observed/{fileName}")
        dataset.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
        dataset.rio.write_crs("epsg:4326", inplace=True)
        basinClipped = dataset.rio.clip(stationGDF.geometry, stationGDF.crs, drop=True)


        observedDate=basinClipped.indexes['time'][0].strftime('%Y-%m-%d')
        # print('File Name: ',fileName,'Observed Date: ', observedDate)


        weights = np.cos(np.deg2rad(basinClipped.lat))
        weights.name = "weights"
        rainfall_weighted = basinClipped.weighted(weights)
        weighted_mean = rainfall_weighted.mean(("lon", "lat"))
        meanPrecipitation=weighted_mean['precipitation'].values.tolist()[0]

        dailyPrecipitationDict[observedDate]=meanPrecipitation

        return dailyPrecipitationDict

    def returnRainfallRecords(self,stationName,givenDate):
            current_year = str(datetime.now().year)
            fileNameList = self.generateDownloadFileNameList(current_year,givenDate)
            # print('File Name List: ', fileNameList)

            dailyPrecipitationDict={}
            for fileName in fileNameList:
                try:
                    # print('Accessing File : ', fileName)
                    dailyPrecipitationDict= self.computeDailyBasinWiseMeanPrecipitation(fileName,stationName,dailyPrecipitationDict)
                except:
                    print(f'Observed File {fileName} Does Not Exist')


            observedRainfallDF=self.generateObservedDataframe(dailyPrecipitationDict)

            # print('Observed Rainfall DF')
            # print(observedRainfallDF)

            forecastPrecipitationDict=self.computeBasinWiseForecast(stationName,givenDate)
            forecastRainfallDF = self.generateForecastDataframe(forecastPrecipitationDict)

            # print('Forecast Rainfall DF')
            # print(forecastRainfallDF)

            rainfallRecords = self.returnDesiredDataframe(observedRainfallDF,forecastRainfallDF)
            # rainfallRecords=[]
            return rainfallRecords

    def processDateTimeDictRainfall(self,givenDate,rainfallRecords,indexedHourThresholdDict):

        # print(rainfallRecords)

        rangeStart = rainfallRecords.iloc[0]['Date']
        rangeStart = datetime.strptime(rangeStart,'%Y-%m-%d')
        rangeEnd = rainfallRecords.iloc[len(rainfallRecords)-1]['Date']
        rangeEnd=datetime.strptime(rangeEnd,'%Y-%m-%d')

        # print('Range Start: ', rangeStart , ' Range End: ',rangeEnd)

        dictRainfall=rainfallRecords.to_dict()
        # dictRainfall.keys()
        timeList=list(dictRainfall['Date'].values())
        rainfallList=list(dictRainfall['Rainfall'].values())
        dictRainfall={}
        for i,j in zip(timeList,rainfallList):
            # dateString=datetime.strftime(i,'%Y-%m-%d')
            # print(i)
            dictRainfall[i]=j


        # indexedHourThresholdDict={0:[24,25], 1:[48,40.5], 2:[72,53.5], 3:[120,76], 4:[168,96], 5:[240,123]}
        intensityThresholdDataframe=pd.DataFrame.from_dict(indexedHourThresholdDict,orient='index',columns=['Hours','Thresholds'])
        # print('Intensity Threshold Dataframe: ')
        # print(intensityThresholdDataframe)
        givenDateInDateTime=datetime.strptime(givenDate,'%Y-%m-%d')
        
        noOfDayWithinRange=(rangeEnd-givenDateInDateTime).days
        # print('No. of Days in range: ', noOfDayWithinRange)

        dateTimeRangeFromGivenDateTime=[givenDateInDateTime+timedelta(days=day) for day in range (0,noOfDayWithinRange+1)]

        return intensityThresholdDataframe,givenDateInDateTime,dateTimeRangeFromGivenDateTime,rangeStart,dictRainfall


    def returnCumulativeRainfall(self,givenDateInDateTime,hourThresholdDict,hourList,rangeStart,dictRainfall):
        
        # givenDateInDateTime=datetime.strptime(givenDate,'%Y-%m-%d')
        totalRainfall= []

        for hour in hourList:
            thresholdOfThatHour=hourThresholdDict[hour]
            noOfDays=int(hour/24)
            cumulativeRainfallList=[]

            for day in range(noOfDays):
                calculatingDate= givenDateInDateTime-timedelta(days=day)
                if (calculatingDate>=rangeStart):
                    # print('Calculating Date: ', calculatingDate)
                    calculatingDateString=datetime.strftime(calculatingDate,'%Y-%m-%d')
                    rainfallOnThatDay= dictRainfall[calculatingDateString]
                    cumulativeRainfallList.append(rainfallOnThatDay)
                else : continue
            # print('----------------------------------------------------------------------')
            sumOfRainfallIntensity=sum(cumulativeRainfallList)
            totalRainfall.append(round(sumOfRainfallIntensity,2))

        return totalRainfall



    def FlashFlood(self,forecast_date,basin_id):

        # print('Basin Id : ', basin_id)
        stationName=stationDict[basin_id]
        print('Working on Basin ID: ', basin_id, ' Name: ', stationName)


        # givenDate = forecast_date
        hourThresholdDict=stationThresholds[basin_id]
        indexedHourThresholdDict=stationThresholdsList[basin_id]
        # print('Index Hour Threshold Dict: ', indexedHourThresholdDict)
        rainfallRecords=self.returnRainfallRecords(stationName,forecast_date)
        # print('Rainfall Records: ')
        # print(rainfallRecords)

        intensityThresholdDataframe,givenDateInDateTime,dateTimeRangeFromGivenDateTime,rangeStart,dictRainfall = self.processDateTimeDictRainfall(forecast_date,rainfallRecords,indexedHourThresholdDict)
        hourList=[24, 48, 72, 120, 168, 240]


        # print('Date Time Range: ', dateTimeRangeFromGivenDateTime)

        for dateTime in dateTimeRangeFromGivenDateTime:

            # print(dateTime)
            totalRainfall=self.returnCumulativeRainfall(dateTime,hourThresholdDict,hourList,rangeStart,dictRainfall)
            dateString=datetime.strftime(dateTime,'%Y-%m-%d')
            intensityThresholdDataframe[dateString]=totalRainfall
        

            # print('Intensity Threshold Dataframe: ',intensityThresholdDataframe )

        # print(intensityThresholdDataframe)
        jsonResult=intensityThresholdDataframe.to_dict()

        # jsonResult={}

        return jsonResult


    def transformIntoDataFrame(self,data_dict,dateInput,basin_id):

        # Prepare a list to hold the rows of data
        rows = []

        # Fixed station_id

        # Iterate through the dictionary
        for date_key, values in data_dict.items():
            # print(data_dict)
            if date_key not in ["Hours", "Thresholds"]:  # Skip the Hours and Thresholds keys
                for index, value in values.items():
                    # Get corresponding hours and thresholds
                    hours = data_dict["Hours"][index]
                    thresholds = data_dict["Thresholds"][index]
                    
                    # Append the row to the list
                    rows.append({
                        'prediction_date':dateInput,
                        'basin_id': basin_id,
                        'hours': hours,
                        'thresholds': thresholds,
                        'date': datetime.strptime(date_key, "%Y-%m-%d").date(),
                        'value': value
                    })

        # Create a DataFrame
        df = pd.DataFrame(rows)

        return df

    def insert_dataframe(self, df):

        # print(df)

        df_to_insert = df[['prediction_date','basin_id','date','hours','thresholds','value']].copy(deep=True)

        for index, row in df_to_insert.iterrows():
            forecast = MonsoonBasinWiseFlashFloodForecast(
                prediction_date=row['prediction_date'],
                basin_id=row['basin_id'],
                date=row['date'],
                hours=row['hours'],
                thresholds=row['thresholds'],
                value=row['value']
            )
            forecast.save()  # Save the instance to the database

    def main(self,dateInput):
        basin_id_list= list(stationDict.keys())

        for basin_id in basin_id_list:
            response = self.FlashFlood(dateInput,basin_id)
            df = self.transformIntoDataFrame(response,dateInput,basin_id)
            print(df)
            self.insert_dataframe(df)
