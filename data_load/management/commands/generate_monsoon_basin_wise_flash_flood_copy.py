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

stationDict = {
    1: 'khaliajhuri',
    2: 'gowainghat',
    3: 'dharmapasha',
    4: 'userbasin',
    5: 'laurergarh',
    6: 'muslimpur',
    7: 'debidwar',
    8: 'ballah',
    9: 'habiganj',
    10: 'parshuram',
    11: 'cumilla',
    12: 'nakuagaon',
    13: 'amalshid'
}

stationThresholds = {
    1: {24: 96.89950599, 48: 162.8320331, 72: 220.5977546, 120: 323.3900146, 168: 416.0549444, 240: 543.4315997},
    2: {24: 62.91949742, 48: 92.91302073, 72: 116.7093532, 120: 155.5491175, 168: 187.9516346, 240: 229.6988847},
    3: {24: 24.5, 48: 41.5, 72: 56.5, 120: 83, 168: 107.5, 240: 141},
    4: {24: 25, 48: 40.5, 72: 53.5, 120: 76, 168: 96, 240: 123},
    5: {24: 52.66627048, 48: 65.83191795, 72: 75.01043443, 120: 88.41715826, 168: 98.53177944, 240: 110.5199031},
    6: {24: 33.50, 48: 51.84, 72: 66.93, 120: 92.34, 168: 114.14, 240: 142.90},
    7: {24: 41.37244531, 48: 59.10820306, 72: 72.82489007, 120: 94.72459479, 168: 112.6349373, 240: 135.331633},
    8: {24: 28.77247366, 48: 35.77137016, 72: 40.63017364, 120: 47.70181973, 168: 53.01955989, 240: 59.30527458},
    9: {24: 14, 48: 22, 72: 30, 120: 44, 168: 56, 240: 73},
    10: {24: 48.53562859, 48: 67.45165462, 72: 81.77158915, 120: 104.2169518, 168: 122.2704102, 240: 144.8339302},
    # 11: {24: 9.732483938, 48: 28.22773042, 72: 52.62513159, 120: 115.3465484, 168: 193.4155288, 240: 334.5467914},
    11: { 24: 36.8802, 48: 60.998, 72: 81.87342, 120: 118.6278, 168: 151.4478,240: 196.2044},

    12: {24: 30.52, 48: 40.468, 72: 47.73, 120: 58.75, 168: 67.37, 240: 77.89},
    13: { 24: 13.04, 48: 22.34, 72: 30.61, 120: 45.52, 168: 59.12, 240: 77.99}

}

stationThresholdsList = {
    1: {0: [24, 96.89950599], 1: [48, 162.8320331], 2: [72, 220.5977546], 3: [120, 323.3900146], 4: [168, 416.0549444], 5: [240, 543.4315997]},
    2: {0: [24, 62.91949742], 1: [48, 92.91302073], 2: [72, 116.7093532], 3: [120, 155.5491175], 4: [168, 187.9516346], 5: [240, 229.6988847]},
    3: {0: [24, 24.5], 1: [48, 41.5], 2: [72, 56.5], 3: [120, 83], 4: [168, 107.5], 5: [240, 141]},
    4: {0: [24, 25], 1: [48, 40.5], 2: [72, 53.5], 3: [120, 76], 4: [168, 96], 5: [240, 123]},
    5: {0: [24, 52.66627048], 1: [48, 65.83191795], 2: [72, 75.01043443], 3: [120, 88.41715826], 4: [168, 98.53177944], 5: [240, 110.5199031]},
    6: {0: [24, 33.50], 1: [48, 51.84], 2: [72, 66.93], 3: [120, 92.34], 4: [168, 114.14], 5: [240, 142.90]},
    7: {0: [24, 41.37244531], 1: [48, 59.10820306], 2: [72, 72.82489007], 3: [120, 94.72459479], 4: [168, 112.6349373], 5: [240, 135.331633]},
    8: {0: [24, 28.77247366], 1: [48, 35.77137016], 2: [72, 40.63017364], 3: [120, 47.70181973], 4: [168, 53.01955989], 5: [240, 59.30527458]},
    9: {0: [24, 14], 1: [48, 22], 2: [72, 30], 3: [120, 44], 4: [168, 56], 5: [240, 73]},
    10: {0: [24, 58.20], 1: [48, 76.29], 2: [72, 89.34], 3: [120, 109.05], 4: [168, 124.35], 5: [240, 142.92]},
    # 11: {0: [24, 9.732483938], 1: [48, 28.22773042], 2: [72, 52.62513159], 3: [120, 115.3465484], 4: [168, 193.4155288], 5: [240, 334.5467914]},
    11: {0: [24, 36.8802], 1: [48, 60.998], 2: [72, 81.87342], 3: [120, 118.6278], 4: [168, 151.4478], 5: [240, 196.2044]},
    12: {0: [24, 30.52], 1: [48, 40.46], 2: [72, 47.73], 3: [120, 58.75], 4: [168, 67.37], 5: [240, 77.89]},
    13: {0: [24, 13.04], 1: [48, 22.34], 2: [72, 30.61], 3: [120, 45.52], 4: [168, 59.12],5: [240, 77.99]}
}


class Command(BaseCommand):
    help = 'Generate Basin Wise Flashflood for Presentday'

    def handle(self, *args, **kwargs):
        try:
            dateInput = kwargs['date']
        except:
            updateDate = datetime.today() - timedelta(days=0)
            dateInput = datetime.strftime(updateDate, '%Y-%m-%d')
        self.main(dateInput)

    def generateDownloadFileNameList(self, downloadYear, givenDate):
        fileNameList = []
        datetimeGivenDate = datetime.strptime(givenDate, "%Y-%m-%d")
        dayOfTheYear = datetimeGivenDate.timetuple().tm_yday
        for i in range(1, 11):
            downloadDay = dayOfTheYear - i
            numberOfDigits = int(math.log10(downloadDay)) + 1
            if numberOfDigits == 2:
                downloadDay = str(downloadDay).rjust(3, '0')
            else:
                downloadDay = str(downloadDay)
            dowanloadFileName = str(downloadYear) + downloadDay + '.nc'
            fileNameList.append(dowanloadFileName)
        return fileNameList

    def generateObservedDataframe(self, dailyPrecipitationDict):
        dateList = list(dailyPrecipitationDict.keys())
        rainfallList = list(dailyPrecipitationDict.values())
        dailyRainfallDict = {'Date': dateList, 'Rainfall': rainfallList}
        observedRainfallDF = pd.DataFrame.from_dict(dailyRainfallDict, orient='columns')
        observedRainfallDF.sort_values(by='Date', inplace=True)
        observedRainfallDF.reset_index(drop=True, inplace=True)
        return observedRainfallDF

    def computeBasinWiseForecast(self, stationName, givenDate):

        dir_path = os.getcwd()

        basin_json_file_path=os.path.join(dir_path,f'assets/floodForecastStations/{stationName}.json')
        # basin_json_file_path = os.path.join(dir_path, f'floodForecastStations/{stationName}.json')
        stationGDF = gpd.read_file(basin_json_file_path, crs="epsg:4326")
        dateString = givenDate[8:10] + givenDate[5:7] + givenDate[:4]
        fileName = dateString + '.nc'

        if stationName != 'cambodia':
            forecast_file_path = os.path.join(dir_path, f'forecast/{fileName}')
        elif stationName == 'cambodia':
            print('In cambodia Forecast ....')
            forecast_file_path = os.path.join(dir_path, f'cambodiaForecast/{fileName}')

        fileExist = os.path.isfile(forecast_file_path)
        if not fileExist:
            previousDate = datetime.strptime(givenDate, '%Y-%m-%d')
            previousDate = previousDate - timedelta(days=1)
            previousDate = datetime.strftime(previousDate, '%Y-%m-%d')
            dateString = previousDate[8:10] + previousDate[5:7] + previousDate[:4]
            fileName = dateString + '.nc'
            if stationName != 'cambodia':
                forecast_file_path = os.path.join(dir_path, f'forecast/{fileName}')
            elif stationName == 'cambodia':
                print('In cambodia Forecast ....')
                forecast_file_path = os.path.join(dir_path, f'cambodiaForecast/{fileName}')

        forecastDataset = xr.open_dataset(forecast_file_path)

        for var in forecastDataset.data_vars:
            forecastDataset[var] = forecastDataset[var].where(forecastDataset[var] < 1e30, 0.0)

        forecastDataset.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude", inplace=True)
        forecastDataset.rio.write_crs("epsg:4326", inplace=True)
        clippedForecast = forecastDataset.rio.clip(stationGDF.geometry, stationGDF.crs, drop=True)
        dateList = list(clippedForecast.indexes['time'].strftime('%Y-%m-%d %H:%M:%S'))
        cumulative_forecast_precipitation = {}

        for thisDay in dateList:
            oneDayData = clippedForecast.sel(time=thisDay)
            weighted_mean = oneDayData.mean(("longitude", "latitude"))
            
            # Aligned with Code 1: Only using cp for total precipitation.
            meancpValue = weighted_mean['cp'].values.tolist()
            # Ensure the value is a scalar, handling if it's a list.
            totalPrecipitation = meancpValue if isinstance(meancpValue, (float, int)) else meancpValue[0]
            
            if math.isnan(totalPrecipitation):
                totalPrecipitation = 0.00
            
            cumulative_forecast_precipitation[thisDay] = totalPrecipitation * 1000

        daily_rainfall_values = {}
        sorted_timestamps = sorted(cumulative_forecast_precipitation.keys())
        
        if sorted_timestamps:
            previous_cumulative = 0.0
            for i, current_timestamp_str in enumerate(sorted_timestamps):
                current_cumulative = cumulative_forecast_precipitation[current_timestamp_str]
                date_only_str = current_timestamp_str[:10]
                
                if i == 0:
                    interval_precip = current_cumulative
                else:
                    interval_precip = current_cumulative - previous_cumulative
                
                if interval_precip < 0:
                    interval_precip = 0.0
                
                if date_only_str not in daily_rainfall_values:
                    daily_rainfall_values[date_only_str] = 0.0
                daily_rainfall_values[date_only_str] += interval_precip
                previous_cumulative = current_cumulative

        for date, value in daily_rainfall_values.items():
            daily_rainfall_values[date] = round(value, 4)

        return daily_rainfall_values

    def generateForecastDataframe(self, forecastPrecipitationDict):
        dateList = list(forecastPrecipitationDict.keys())
        rainfallList = list(forecastPrecipitationDict.values())
        dailyRainfallDict = {'Date': dateList, 'Rainfall': rainfallList}
        forecastRainfallDF = pd.DataFrame.from_dict(dailyRainfallDict, orient='columns')
        forecastRainfallDF.sort_values(by='Date', inplace=True)
        forecastRainfallDF.reset_index(drop=True, inplace=True)
        return forecastRainfallDF

    def returnDesiredDataframe(self, observedRainfallDF, forecastRainfallDF):
        requiredDF = pd.concat([observedRainfallDF, forecastRainfallDF])
        requiredDF.reset_index(drop=True, inplace=True)
        return requiredDF

    def computeDailyBasinWiseMeanPrecipitation(self, fileName, stationName, dailyPrecipitationDict):

        # print('I am in computeDailyBasinWiseMeanPrecipitation Functon')

        station_json_path = os.path.join(settings.BASE_DIR, 'assets', 'floodForecastStations', f'{stationName}.json')
        stationGDF = gpd.read_file(station_json_path, crs="epsg:4326")
        # stationGDF = gpd.read_file(f'floodForecastStations/{stationName}.json', crs="epsg:4326")

        # print('I was able to read station GDF : ', stationGDF)

        # dataset = xr.open_dataset(f"observed/{fileName}")
        file_path = os.path.join(settings.BASE_DIR, 'observed', fileName)
        # print('File Path is: ', file_path)
        dataset = xr.open_dataset(file_path)
        dataset['precipitation'] = dataset['precipitation'].where(dataset['precipitation'] < 1e30, np.nan)

        
        dataset.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=True)
        dataset.rio.write_crs("epsg:4326", inplace=True)
        basinClipped = dataset.rio.clip(stationGDF.geometry, stationGDF.crs, drop=True)
        observedDate = basinClipped.indexes['time'][0].strftime('%Y-%m-%d')
        weights = np.cos(np.deg2rad(basinClipped.lat))
        weights.name = "weights"
        rainfall_weighted = basinClipped.weighted(weights)
        weighted_mean = rainfall_weighted.mean(("lon", "lat"))
        meanPrecipitation = weighted_mean['precipitation'].values.tolist()[0]
        dailyPrecipitationDict[observedDate] = meanPrecipitation
        return dailyPrecipitationDict

    def returnRainfallRecords(self, stationName, givenDate):
        print(' I am in returnRainfallRecords Function . .')
        current_year = str(datetime.now().year)
        fileNameList = self.generateDownloadFileNameList(current_year, givenDate)
        print('File name List: ',fileNameList)
        dailyPrecipitationDict = {}
        for fileName in fileNameList:
            try:
                dailyPrecipitationDict = self.computeDailyBasinWiseMeanPrecipitation(fileName, stationName, dailyPrecipitationDict)
            except:
                print(f'Observed File {fileName} Does Not Exist')
        observedRainfallDF = self.generateObservedDataframe(dailyPrecipitationDict)
        forecastPrecipitationDict = self.computeBasinWiseForecast(stationName, givenDate)
        forecastRainfallDF = self.generateForecastDataframe(forecastPrecipitationDict)
        rainfallRecords = self.returnDesiredDataframe(observedRainfallDF, forecastRainfallDF)
        return rainfallRecords

    def processDateTimeDictRainfall(self, givenDate, rainfallRecords, indexedHourThresholdDict):
        rangeStart = rainfallRecords.iloc[0]['Date']
        rangeStart = datetime.strptime(rangeStart, '%Y-%m-%d')
        rangeEnd = rainfallRecords.iloc[len(rainfallRecords) - 1]['Date']
        rangeEnd = datetime.strptime(rangeEnd, '%Y-%m-%d')
        dictRainfall = rainfallRecords.to_dict()
        timeList = list(dictRainfall['Date'].values())
        rainfallList = list(dictRainfall['Rainfall'].values())
        dictRainfall = {}
        for i, j in zip(timeList, rainfallList):
            dictRainfall[i] = j
        intensityThresholdDataframe = pd.DataFrame.from_dict(indexedHourThresholdDict, orient='index', columns=['Hours', 'Thresholds'])
        givenDateInDateTime = datetime.strptime(givenDate, '%Y-%m-%d')
        noOfDayWithinRange = (rangeEnd - givenDateInDateTime).days
        dateTimeRangeFromGivenDateTime = [givenDateInDateTime + timedelta(days=day) for day in range(0, noOfDayWithinRange + 1)]
        return intensityThresholdDataframe, givenDateInDateTime, dateTimeRangeFromGivenDateTime, rangeStart, dictRainfall

    def returnCumulativeRainfall(self, givenDateInDateTime, hourThresholdDict, hourList, rangeStart, dictRainfall):
        
        totalRainfall = []

        for hour in hourList:
            # Removed the problematic line that was trying to access an index on a float
            # The value from the dictionary is used directly.
            
            noOfDays = int(hour / 24)
            cumulativeRainfallList = []

            for day in range(noOfDays):
                calculatingDate = givenDateInDateTime - timedelta(days=day)
                if (calculatingDate >= rangeStart):
                    calculatingDateString = datetime.strftime(calculatingDate, '%Y-%m-%d')
                    rainfallOnThatDay = dictRainfall[calculatingDateString]
                    cumulativeRainfallList.append(rainfallOnThatDay)
                else:
                    continue

            sumOfRainfallIntensity = sum(cumulativeRainfallList)
            totalRainfall.append(round(sumOfRainfallIntensity, 2))

        return totalRainfall

    def FlashFlood(self, forecast_date, basin_id):
        print("I have made a chage ")
        stationName = stationDict[basin_id]
        print('Working on Basin ID: ', basin_id, ' Name: ', stationName)
        hourThresholdDict = stationThresholds[basin_id]
        indexedHourThresholdDict = stationThresholdsList[basin_id]
        rainfallRecords = self.returnRainfallRecords(stationName, forecast_date)
        intensityThresholdDataframe, givenDateInDateTime, dateTimeRangeFromGivenDateTime, rangeStart, dictRainfall = self.processDateTimeDictRainfall(forecast_date, rainfallRecords, indexedHourThresholdDict)
        hourList = [24, 48, 72, 120, 168, 240]
        for dateTime in dateTimeRangeFromGivenDateTime:
            totalRainfall = self.returnCumulativeRainfall(dateTime, hourThresholdDict, hourList, rangeStart, dictRainfall)
            dateString = datetime.strftime(dateTime, '%Y-%m-%d')
            intensityThresholdDataframe[dateString] = totalRainfall
        jsonResult = intensityThresholdDataframe.to_dict()
        return jsonResult

    def transformIntoDataFrame(self, data_dict, dateInput, basin_id):
        rows = []
        for date_key, values in data_dict.items():
            if date_key not in ["Hours", "Thresholds"]:
                for index, value in values.items():
                    hours = data_dict["Hours"][index]
                    thresholds = data_dict["Thresholds"][index]
                    rows.append({
                        'prediction_date': dateInput,
                        'basin_id': basin_id,
                        'hours': hours,
                        'thresholds': thresholds,
                        'date': datetime.strptime(date_key, "%Y-%m-%d").date(),
                        'value': value
                    })
        df = pd.DataFrame(rows)
        return df

    def insert_dataframe(self, df):
        if not df.empty:
            df = df.replace([np.inf, -np.inf], 0.0)
            df = df.fillna(0.0)

            prediction_date = df['prediction_date'].iloc[0]
            basin_id = df['basin_id'].iloc[0]
            MonsoonBasinWiseFlashFloodForecast.objects.filter(prediction_date=prediction_date, basin_id=basin_id).delete()
        df_to_insert = df[['prediction_date', 'basin_id', 'date', 'hours', 'thresholds', 'value']].copy(deep=True)
        for index, row in df_to_insert.iterrows():
            # MonsoonBasinWiseFlashFloodForecast
            forecast = MonsoonBasinWiseFlashFloodForecast(
                prediction_date=row['prediction_date'],
                basin_id=row['basin_id'],
                date=row['date'],
                hours=row['hours'],
                thresholds=row['thresholds'],
                value=row['value']
            )
            forecast.save()

    def main(self, dateInput):
        print('I am in the Main Function .. ')
        basin_id_list = list(stationDict.keys())
        for basin_id in basin_id_list:
            response = self.FlashFlood(dateInput, basin_id)
            df = self.transformIntoDataFrame(response, dateInput, basin_id)
            print(df)
            self.insert_dataframe(df)