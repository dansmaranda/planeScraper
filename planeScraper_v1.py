import json
import requests
from lxml import html
from collections import OrderedDict
import argparse
from  pprint import pprint as pp
import random

from halo import Halo
from colorama import Fore, Back, Style

from matplotlib.pyplot import colorbar
import matplotlib.pyplot as plt

from datetime import *
import os


nbrTerminalRows, nbrTerminalCols = os.popen('stty size', 'r').read().split()
nbrTerminalRows = int(nbrTerminalRows)
nbrTerminalCols = int(nbrTerminalCols)
delimitator = '\n' + '▓' * nbrTerminalCols + '\n'
delimitator2 = '\n' + '-' * nbrTerminalCols + '\n'
delimitator3 = '\n' + ' ' * nbrTerminalCols + '\n'
FNULL = open(os.devnull, 'w')

class planeScraper:
    '''
        Wee little class to get the cheapest and most time efficient flights from Expedia. Analyses if you want to go on a holiday, just want the cheapest journey onw way or something of the sorts.

    '''
    # REQUEST_ID_REGEX = r"data-leg-natural-key=\"(\w+)\">"

    def __init__(self, departAirp, arrivAirp, departDate, returnDate = None):
        '''
            NEEDS CROSSCHECK with list of location/iata codes. !!!!!

            Initialises the class instance for the journey with the following attributes:

            Args:
                - departAirp            ::          Type: <str> . IATA code that specifies the Departure airport (E.g. if we're leaving from Glasgow the IATA code is GLA).

                - arrivAirp             ::          Type: <str> . IATA code that specifies the Return airport (E.g. if we're returning from Bucharest the IATA code is BUH).

                - departDate            ::          Type: <str> or <datetime> . Departure date that is either specified in the usual international format DD/MM/YYYY as a string and is then formatted (e.g. 10/12/2018 as December 10th 2018) or as a datetime object.

            Optional Args:
                - returnDate            ::          Type: <str> or <datetime>. Same as "departDate". If NOT specified the class then the rest of the class will treat it as a the one way flight form departAirp to arrivAirp on the departDate. IF SPECIFIED then we store the return information which is then available for further purpouses.

            Returns:
                - None
        '''

        # Maybe introduce some cleaning / formatting tool here?
        self.departAirp = departAirp
        self.arrivAirp = arrivAirp

        # ADD CROSSCHECK WITH AIRPORT DATABASE, also introduce location/iata code mathcer
        # print (type(departDate)==str)
        if type(departDate)==str:
            dateVec = [int (dateBit) for dateBit in departDate.split('/')]
            self.departDate = date( dateVec[2], dateVec[1], dateVec[0])
        else:
            self.departDate = departDate

        if returnDate != None:
            if type(returnDate)==str :
                dateVec2 = [int (dateBit) for dateBit in returnDate.split('/')]
                self.returnDate = date( dateVec2[2], dateVec2[1], dateVec2[0])
            else:
                self.returnDate = returnDate
        else:
            self.returnDate = None



        # print (delimitator)
        # print('Got Flight details! Proceeding to get combinations for dates.')
        # if returnDate:
        #     print ('Number of Days on stay: ', self.returnDate - self.departDate)
        #     print (delimitator)

    def _makeFlightsDictHead(self, flightDataDict):
        '''
            Makes a flight dictionary head for a class instance that contains 'FlightAttributes' and  an empty dictionary 'Flights'.
            'FlightAttributes' : { 'Airports' : {'Departure' : ... , 'Arrival' : ... },
                                   'Currency' : ... ,
                                   'TimeUnit' : ... }

            Arguments:
                - flightDataDict            ::          Type: <dict> . 'Processed' Fligh Data dictionary resulting form the expedia HTML request (i.e. not raw json).
        '''
        flightsDict = {}
        flightsDict['FlightAttributes'] = { }

        flightsDict['FlightAttributes']['Airports'] = {'Departure' : self.departAirp, 'Arrival': self.arrivAirp}
        flightsDict['FlightAttributes']['Currency'] = flightDataDict['legs'][
                                  random.choice(list(flightDataDict['legs']))]['price']['currencyCode']
        flightsDict['FlightAttributes']['TimeUnit'] = 'Hours'
        flightsDict['Flights'] = {}

        return flightsDict

    def _makeFlightInfoDict(self, flightDataDict, flightID, flightWay):
        '''
        '''

        flightInfo = {}
        flightInfo['FlightWay'] = flightWay

        if flightWay == 'Return':

            flightInfo['Price'] = round (flightDataDict['legs'][flightID]['price']['bestPriceDelta'], 2)

        elif flightWay == 'Outbound':

            flightInfo['Price'] = round (flightDataDict['legs'][flightID]['price']['exactPrice'], 2)


        flightInfo['Airline'] = flightDataDict['legs'][flightID]['carrierSummary']['airlineName']
        flightInfo['Stops'] = flightDataDict['legs'][flightID]['stops']

        auxTime = timedelta( hours = flightDataDict['legs'][flightID]['duration']['hours'],
                             minutes = flightDataDict['legs'][flightID]['duration']['minutes'])
        flightInfo['TotalFlightTime'] = round( auxTime.total_seconds()/3600, 2 )




        flightCodeStr = ''
        for stopNb in range ( len( flightDataDict['legs'][flightID]['timeline'] ) ):

            if 'carrier' in flightDataDict['legs'][flightID]['timeline'][stopNb].keys():

                flightCodeStr += \
                    ( flightDataDict['legs'][flightID]['timeline'][stopNb]['carrier']['airlineCode'] +             flightDataDict['legs'][flightID]['timeline'][stopNb]['carrier']['flightNumber'] )

                flightCodeStr += '_' # Modify end carriage below if replacing '_'
        flightInfo['FlightCode'] = flightCodeStr[:-1]


        return flightInfo

    def _makeReturnFlightFromDicts(self, flightInfo_Out, flightInfo_Return):
        '''
        '''

        flightInfo = {}


        flightInfo['FlightTimeOut'] =    flightInfo_Out['TotalFlightTime']
        flightInfo['FlightTimeReturn'] = flightInfo_Return['TotalFlightTime']

        flightInfo['StopsOut'] =    flightInfo_Out['Stops']
        flightInfo['StopsReturn'] = flightInfo_Return['Stops']

        flightInfo['PriceOut'] =    flightInfo_Out['Price']
        flightInfo['PriceReturn'] = flightInfo_Return['Price']

        for attributeToAdd in ['FlightCode', 'TotalFlightTime', 'Price']:
            if attributeToAdd == 'FlightCode':
                flightInfo[attributeToAdd] = flightInfo_Out[attributeToAdd] + '::' + flightInfo_Return[attributeToAdd]
            else:
                flightInfo[attributeToAdd] = flightInfo_Out[attributeToAdd] + flightInfo_Return[attributeToAdd]
        return flightInfo

    def _writeToCache(self, flightsDict):
        '''
        '''
        from time import strftime, gmtime
        cacheFileName = 'CacheFile_' + self.departAirp +'->' +self.arrivAirp + \
                        '_' + strftime("%d%m%Y-%H%M%S", gmtime())

        with open('Cache/' + cacheFileName + '.json', 'w') as outCacheFile:
            json.dump(flightsDict, outCacheFile)

    def _getFlightInfoSingle(self, writeToCache = False):
        '''
            To be called by get FlightInfo if the flight is one way
        '''
        expediaURL = "https://www.expedia.com/Flights-Search?trip=oneway&leg1=from%3A{0}%2Cto%3A{1}%2Cdeparture%3A{2}%2F{3}%2F{4}TANYT&passengers=adults%3A1%2Cchildren%3A0%2Cseniors%3A0%2Cinfantinlap%3AY&options=cabinclass%3Aeconomy&mode=search&origref=www.expedia.com".format(
            self.departAirp, self.arrivAirp,
            str(wkPS.departDate.month), str(wkPS.departDate.day), str(wkPS.departDate.year))

        # print(expediaURL)


        expediaResp = requests.get(expediaURL)
        parser = html.fromstring(expediaResp.text)
        json_data_xpath = parser.xpath("//script[@id='cachedResultsJson']//text()")


        raw_json = json.loads(json_data_xpath[0] if json_data_xpath else '')
        flightDataDict = json.loads(raw_json["content"])
        # pp (flightDataDict['index'])

        flightsDict = self._makeFlightsDictHead(flightDataDict)

        for flightID, flightCount in zip( flightDataDict['legs'].keys(),
                range( len(flightDataDict['legs'].keys())) ):

            flightInfo = self._makeFlightInfoDict(flightDataDict, flightID, 'Outbound')
            flightsDict['Flights']['Flight-'+str(flightCount+1)] = flightInfo
            del(flightInfo)

        if writeToCache:
            self._writeToCache(self, flightsDict)

        return flightsDict

    # def _getExpedia(expediaURL):
    #
    #     expediaResp = requests.get(expediaURL)
    #     parser = html.fromstring(expediaResp.text)
    #     json_data_xpath = parser.xpath("//script[@id='cachedResultsJson']//text()")
    #
    #     raw_json = json.loads(json_data_xpath[0] if json_data_xpath else '')
    #     flightDataDictOutBound = json.loads(raw_json["content"])
    #
    #     return expediaResp,

    def _getFlightInfoReturn(self, writeToCache = False):
        '''
            To be called if we have a return flight
        '''
        spinner = Halo(text='Getting Return Flight Info. Might take a while', spinner='dots')
        spinner.start()

        # headers = {}
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}


        expediaURL = "https://www.expedia.com/Flights-Search?flight-type=on&starDate={0}%2F{1}%2F{2}&endDate={3}%2F{4}%2F{5}&mode=search&trip=roundtrip&leg1=from%3A{6}%2Cto%3A{7}%2Cdeparture%3A{0}%2F{1}%2F{2}TANYT&leg2=from%3A{7}%2Cto%3A{6}%2Cdeparture%3A{3}%2F{4}%2F{5}TANYT&passengers=adults%3A1%2Cchildren%3A0%2Cseniors%3A0%2Cinfantinlap%3AY&options=cabinclass%3Aeconomy&mode=search&origref=www.expedia.com".format(
            str(self.departDate.month), str(self.departDate.day), str(self.departDate.year),
            str(self.returnDate.month), str(self.returnDate.day), str(self.returnDate.year),
            self.departAirp, self.arrivAirp )
        #
        # print(expediaURL)
        # print(delimitator3)
        # import time
        # time.sleep(3)


        with requests.Session() as s:


            # Super ad hoc open a browser and fake the visit so i can get that sweet sweet data
            from selenium import webdriver

            driver = webdriver.Safari()
            driver.get(expediaURL)
            import time
            time.sleep(10)


            #########################################################################

            expediaResp = s.get(expediaURL, headers = headers, verify=True)

            parser = html.fromstring(expediaResp.text)
            json_data_xpath = parser.xpath("//script[@id='cachedResultsJson']//text()")
            raw_json = json.loads(json_data_xpath[0] if json_data_xpath else '')

            print ('\nExpedia :',expediaResp.status_code)


            flightDataDictOutBound = json.loads(raw_json["content"])
            #  Maybe find another way around this without using Eleme⁠nt?

            from pattern.web import Element
            el1 = Element(expediaResp.content)
            departure_request_id = el1("div#originalContinuationId")[0].content



            flightsDict = self._makeFlightsDictHead( flightDataDictOutBound )
            failedJSONList = [];

            count = 0
            for  flightNb_Outbound, flightID_Outbound in enumerate(flightDataDictOutBound['legs'].keys()):
                if count ==3 :
                    break
                # print(flightID_Outbound, flightNb_Outbound)
                count +=1
                flightInfo_Out = self._makeFlightInfoDict(flightDataDictOutBound, flightID_Outbound, 'Outbound')

                json_url = "https://www.expedia.com/Flight-Search-Paging?c={DEPT_ID}&is=1" \
                "&fl0={ARRV_ID}&sp=asc&cz=200&cn=0&ul=1"
                json_url = json_url.format(
                    DEPT_ID=departure_request_id,
                    ARRV_ID=list(flightDataDictOutBound['legs'].keys())[flightNb_Outbound]
                )

                # print(json_url)
                # time.sleep(2)

                get_request = s.get(json_url, headers = headers)
                print ('\nJson:', get_request.status_code)

                try:
                    get_request.raise_for_status()
                except:
                    print(f"Status code: {get_request.status_codes}")


                parser = html.fromstring(get_request.text)
                flightDataDictReturn = get_request.json()['content']

                # IF we get a non empty return response then we proceed

                if flightDataDictReturn['legs']:
                    print ('\n'+Fore.GREEN + 'νν SUCCESS!!' + Style.RESET_ALL)

                    for  flightNb_Return, flightID_Return in enumerate(flightDataDictReturn['legs'].keys()):

                        # This is the continuation statement when the Outbound and Return have the same id since this combination is just a relic and not possible
                        if flightID_Outbound == flightID_Return :
                            # print(flightID_Outbound, flightID_Return)
                            continue

                        flightInfo_Return = self._makeFlightInfoDict(flightDataDictReturn, flightID_Return, 'Return')
                        flightInfo = self._makeReturnFlightFromDicts(flightInfo_Out, flightInfo_Return)

                        flightsDict['Flights']['Flight-O'+str(flightNb_Outbound+1) + '-R' + str(flightNb_Return+1) ] = flightInfo
                        # pp (flightInfo)
                        del(flightInfo)
                else:
                    print ('\n'+Fore.RED + '×× FAILED !!' + Style.RESET_ALL)
                    failedJSONList.append({"JsonURL" :json_url, "FlightInfo":[flightNb_Outbound, flightID_Outbound]})


                    # print(delimitator)

            self._writeToCache(flightsDict)
            stopSymbol = Fore.GREEN+'✓' + Style.RESET_ALL

            spinner.stop_and_persist(symbol=stopSymbol, text='Got Flight Info.')
            del flightDataDictOutBound, flightDataDictReturn




            driver.close()
        # print (delimitator)
        return flightsDict

    def getFlightInfo(self, writeToCache = False):
        '''
            ADD DOCUMENTATION
        '''

        # STILL USING TEST URL PUT IN .format(...)
        if not(self.returnDate):
            return self._getFlightInfoSingle(writeToCache)

        else:
            # PUT IN RETURN URL
            expediaURL2 = "https://www.expedia.com/Flights-Search?flight-type=on&starDate={0}%2F{1}%2F{2}&endDate={3}%2F{4}%2F{5}&mode=search&trip=roundtrip&leg1=from%3A{6}%2Cto%3A{7}%2Cdeparture%3A{0}%2F{1}%2F{2}TANYT&leg2=from%3A{7}%2Cto%3A{6}%2Cdeparture%3A{3}%2F{4}%2F{5}TANYT&passengers=adults%3A1%2Cchildren%3A0%2Cseniors%3A0%2Cinfantinlap%3AY&options=cabinclass%3Aeconomy&mode=search&origref=www.expedia.com".format(
                str(wkPS.departDate.month), str(wkPS.departDate.day), str(wkPS.departDate.year),
                str(wkPS.returnDate.month), str(wkPS.returnDate.day), str(wkPS.returnDate.year),
                self.departAirp, self.arrivAirp
            )
            print(expediaURL2)

            print ('Got Return')



        # expediaResp = requests.get(expediaURL)
        # parser = html.fromstring(expediaResp.text)
        # json_data_xpath = parser.xpath("//script[@id='cachedResultsJson']//text()")
        #
        #
        #
        # raw_json = json.loads(json_data_xpath[0] if json_data_xpath else '')
        # flightDataDict = json.loads(raw_json["content"])
        # pp (flightDataDict['index'])


        flightsDict = {}
        # flightsDict['FlightAttributes'] = { }
        #
        # flightsDict['FlightAttributes']['Airports'] = {'Departure' : self.departAirp, 'Arrival': self.arrivAirp}
        # flightsDict['FlightAttributes']['Currency'] = flightDataDict['legs'][
        #                           random.choice(list(flightDataDict['legs']))]['price']['currencyCode']
        # flightsDict['FlightAttributes']['TimeUnit'] = 'Hours'
        # flightsDict['Flights'] = {}

        if self.returnDate:


            # expediaURL2 = base_url.format(
            #     DEPT_AIRPORT=self.departAirp,
            #     RETURN_AIRPORT=self.arrivAirp,
            #     DEPT_DATE='31%2F10%2F2018',
            #     RETURN_DATE='13%2F11%2F2018'
            # )
            # payload = {'origref':'www.expedia.co.uk#leg/3509c5c928d58c38bc7c4f8a174f7743'}

            from pattern.web import Element

            # print(expediaURL2)
            expediaResp2 = requests.get(expediaURL2)

            parser = html.fromstring(expediaResp2.text)
            json_data_xpath = parser.xpath("//script[@id='cachedResultsJson']//text()")

            raw_json = json.loads(json_data_xpath[0] if json_data_xpath else '')
            flightDataDict = json.loads(raw_json["content"])
            # pp ()

            el1 = Element(expediaResp2.content)

            # print ( el1 )
            import re
            import logging

            departure_request_id = el1("div#originalContinuationId")[0].content
            print(departure_request_id)



            # arrival_request_content = el1("div.flex-card")[0].content
            # arrival_request_id = re.search(self.REQUEST_ID_REGEX, arrival_request_content)

            # try:
            #     arrival_request_id = arrival_request_id.group(1)
            # except AttributeError:
            #     print("Cannot find arrival request ID!")
            #
            #     arrival_request_id = ""
            #
            # print (arrival_request_id)

            json_url = "https://www.expedia.com/Flight-Search-Paging?c={DEPT_ID}&is=1" \
            "&fl0={ARRV_ID}&sp=asc&cz=200&cn=0&ul=1"



            # insert the two request ids
            json_url = json_url.format(
                DEPT_ID=departure_request_id,
                ARRV_ID=list(flightDataDict['legs'].keys())[0]
            )
            print(json_url)

            get_request = requests.get(json_url)

            parser = html.fromstring(get_request.text)
            data_dict = get_request.json()
            # pp(get_request.text)
            # json_data_xpath = parser.xpath("//script[@id='cachedResultsJson']//text()")
            #
            # raw_json = json.loads(json_data_xpath[0] if json_data_xpath else '')
            # flightDataDict2 = json.loads(raw_json["content"])
            # # pp ()
            # pp (flightDataDict2)
            e = Element(get_request.content)

            #
            # import urllib2
            # data_dict = json.load(urllib2.urlopen(json_url))
            # data_dict = json.loads(e.content)

        # get just the flight-related data
            data_dict = data_dict["content"]["legs"]

            pp(data_dict.keys())
            #  json_url = "https://www.expedia.com/Flight-Search-Paging?c={DEPT_ID}&is=1" \
            # "&fl0={ARRV_ID}&sp=asc&cz=200&cn=0&ul=1"

            exit()

            parser = html.fromstring(expediaResp2.text)
            json_data_xpath = parser.xpath("//script[@id='cachedResultsJson']//text()")



            raw_json = json.loads(json_data_xpath[0] if json_data_xpath else '')
            # pp(raw_json)
            flightDataDict = json.loads(raw_json["content"])
            pp(flightDataDict['omniture'])
            for flightID in flightDataDict['legs'].keys():
                pp (flightDataDict['legs'][flightID]['arrivalLocation'])
            # pp (raw_json['metaData'])
            # pp(flightDataDict['offers'])
            pp (raw_json['metaData'])

            findString = '2018-11-04t06:00:00-00:00-coach-gla-ams-kl-1470-coach-ams-otp-kl-1373;2018-11-10t06:00:00+02:00-coach-otp-ams-kl-1372-coach-ams-gla-kl-1473;'


            for returnIndex in flightDataDict['index']:
                print ('Return Price in £ :  ',round (flightDataDict['offers'][returnIndex]['price']['exactPrice'],2))
                legIds = flightDataDict['offers'][returnIndex]['legIds']

                printBool = True

                for legID in legIds:

                    if flightDataDict['legs'][legID]['carrierSummary']['airlineName'] != 'KLM':
                        printBool = False

                for legID in legIds:
                    if printBool == True:
                        print  ( legID)

                        pp(flightDataDict['legs'][legID]['arrivalLocation'])
                        pp(flightDataDict['legs'][legID]['duration'])
                        pp(flightDataDict['legs'][legID]['carrierSummary']['airlineName'])

                print (delimitator)\


            # legIds = ['f69f4997059d4d28ab2f1088b633da0d', 'cdeb33a29a7cb69607afb98c9d0cde06']



        else:

            for flightID, flightCount in zip( flightDataDict['legs'].keys(),
                    range( len(flightDataDict['legs'].keys())) ):
                flightInfo = {}

                flightInfo['Price'] = round (flightDataDict['legs'][flightID]['price']['exactPrice'], 2)
                flightInfo['Airline'] = flightDataDict['legs'][flightID]['carrierSummary']['airlineName']
                flightInfo['Stops'] = flightDataDict['legs'][flightID]['stops']

                auxTime = timedelta( hours = flightDataDict['legs'][flightID]['duration']['hours'],
                               minutes = flightDataDict['legs'][flightID]['duration']['minutes'])

                flightInfo['FlightTime'] = round( auxTime.total_seconds()/3600, 2 )

                # {
                #                             'TimeDelta' : auxTime.total_seconds(),
                #                             'Formatted' : str(auxTime) }



                flightCodeStr = ''
                for stopNb in range ( len( flightDataDict['legs'][flightID]['timeline'] ) ):

                    if 'carrier' in flightDataDict['legs'][flightID]['timeline'][stopNb].keys():

                        flightCodeStr += \
                            (flightDataDict['legs'][flightID]['timeline'][stopNb]['carrier']['airlineCode'] + flightDataDict['legs'][flightID]['timeline'][stopNb]['carrier']['flightNumber'])

                        flightCodeStr += '$\\rightarrow$' #Modify below if replacing →

                flightInfo['FlightCode'] = flightCodeStr[:-13]
                # pp (flightDataDict['legs'][flightID]['timeline'])
                # print ('Flight-'+str(flightCount+1))
                # pp (flightInfo)


                flightsDict['Flights']['Flight-'+str(flightCount+1)] = flightInfo
                del(flightInfo)


        # from time import strftime, gmtime
        # cacheFileName = 'CacheFile_' + self.departAirp +'->' +self.arrivAirp + \
        #                 '_' + strftime("%d%m%Y-%H%M%S", gmtime())
        #
        # with open('Cache/' + cacheFileName + '.json', 'w') as outCacheFile:
        #     json.dump(flightsDict, outCacheFile)

        return flightsDict
        # except:
        #     print('Error: Failed to process page.')

    def _makeAxisFromDict(self, flightsDict, xAxisHandle, yAxisHandle, colorAxisHandle):
        '''
            Seems redundant?

        '''

        xAxis = []
        yAxis = []
        colorAxis = []
        labelAxis = []

        for flightNb in flightsDict['Flights'].keys():

            # if flightsDict['Flights'][flightNb]['FlightTimeOut'] == 12.17 and flightsDict['Flights'][flightNb]['FlightTimeReturn'] == 6.33:
            #     # print( flightNb, flightsDict['Flights'][flightNb]['FlightTimeOut'], flightsDict['Flights'][flightNb]['FlightTimeReturn'] , round(flightsDict['Flights'][flightNb]['Price'],2), '\n',
            #     flightsDict['Flights'][flightNb]['FlightCode'], '\n')

            for axis, axisHandle in zip([xAxis, yAxis, colorAxis], [ xAxisHandle, yAxisHandle, colorAxisHandle]):
                axis.append( flightsDict['Flights'][flightNb][axisHandle] )

        # print (delimitator2)

        # exit()
        return {'xAxis' : xAxis, 'yAxis': yAxis, 'colorAxis':colorAxis , 'labelAxis':labelAxis}

    def _makeAxis_Multiple(self, flightsDict, axisHandles):
        '''
        '''
        axisDict = {}
        for axisHandle in axisHandles:
            axisDict[axisHandle] = []

        for flightNb in flightsDict['Flights'].keys():
            axisOut = []

            for axisHandle in axisHandles:
                axisDict[axisHandle].append( flightsDict['Flights'][flightNb][axisHandle] )

        return axisDict

    def _getChiSquared(self, flightsDict, constrStdevs):

        '''
            DOCUMENTATION NEEDED!!!
                constrStdevs = {'Price': σ_Price, 'FlightTime' : σ_FlightTime }
        '''

        chi2Dict = {}

        for flightNb in flightsDict['Flights'].keys():

            flightChi2 = 0
            for chi2Constr in constrStdevs.keys():
                # print (constrStdevs[chi2Constr]['Ideal'] , flightsDict['Flights'][flightNb][chi2Constr])

                chi2 =  constrStdevs[chi2Constr]['Weight'] * ( (flightsDict['Flights'][flightNb][chi2Constr] - constrStdevs[chi2Constr]['Ideal'])**2) /       ((constrStdevs[chi2Constr]['Std'])**2)

                flightChi2 += chi2
                # print (flightNb, chi2Constr,  flightsDict['Flights'][flightNb][chi2Constr], constrStdevs[chi2Constr])

            chi2Dict[flightNb] = flightChi2
            # print (delimitator)

        return chi2Dict

    def _filterOutBuisness(self, flightsDict):
        '''
        '''

        outRetDict = {}

        for flightNb in flightsDict['Flights'].keys():
            outNb_raw, returnNb_raw = flightNb.split('-')[1], flightNb.split('-')[2]

            outNb = outNb_raw.replace('O', '')
            returnNb = returnNb_raw.replace('R', '')

            if outNb in outRetDict.keys():
                outRetDict[outNb].append(returnNb)
            else:
                outRetDict[outNb] = []
                outRetDict[outNb].append(returnNb)



        # pp (outRetDict)
        # countDuplicates = 0
        # print('Initialy have ', len( list(flightsDict['Flights'].keys() ) ))

        for outNb in outRetDict.keys():
            uniqueList = []
            for returnNb in outRetDict[outNb]:
                candidateCode =  flightsDict['Flights']['Flight-O' + outNb + '-R' + returnNb]['FlightCode']
                if  candidateCode not in uniqueList:
                    uniqueList.append(candidateCode)
                else:
                    # print(candidateCode)
                    # countDuplicates +=1
                    del (flightsDict['Flights']['Flight-O' + outNb + '-R' + returnNb])

        # print('After cleaning have ', len( list(flightsDict['Flights'].keys() ) ))

        # pp(flightsDict['Flights'])
            # print(len (uniqueList))
        # print(countDuplicates)
            # pp (flightsDict['Flights'][flightNb]['FlightCode'])

    def _applyHardCuts(self, flightsDict, cutsDict):
        '''
            ADD DOCUMENTATION!!
        '''
        flightList = list (flightsDict['Flights'].keys())

        for flightNb in flightList:

            for cut in cutsDict.keys():

                # print (flightNb)
                # print (flightsDict['Flights'][flightNb])
                # print (cutsDict[cut], delimitator3)

                if flightsDict['Flights'][flightNb][cut] > cutsDict[cut]:
                    del flightsDict['Flights'][flightNb]
                    break

        return flightsDict

    def plotFlights(self, flightsDict, xAxisHandle, yAxisHandle, colorAxisHandle, axisLabels, cutsDict, colorMap = 'RdBu_r', constrList = ['Price', 'TotalFlightTime'],  priceWeight = 0.5, nbOfShows = 10):
        '''
        '''
        plt.rc('font', size = 40)
        plt.rc('text', usetex=True)
        fig,ax = plt.subplots(figsize=(20, 7))

        flightsDict = self._applyHardCuts(flightsDict, cutsDict)

        # print('Initialy have ', len( list(flightsDict['Flights'].keys() ) ), ' flights.')
        # self._filterOutBuisness(flightsDict)
        # print('After Buisness cleaning have ', len( list(flightsDict['Flights'].keys()) ) , ' flights.')

        # exit()

        axisDict = self._makeAxisFromDict(flightsDict, xAxisHandle, yAxisHandle, colorAxisHandle)
        # matplotlib labels here !!
        names = axisDict['labelAxis']

        sc = plt.scatter ( axisDict['xAxis'], axisDict['yAxis'],
                                    c = axisDict['colorAxis'] ,
                                    cmap = colorMap  , alpha = 1,   s= 40, marker='+')

        # for axisIndex ,xAxisValue in enumerate(axisDict['xAxis']):
        #     if xAxisValue == 8.5 and axisDict['yAxis'][axisIndex] == 5.67:
        #         print (xAxisValue, axisDict['yAxis'][axisIndex], axisDict['colorAxis'][axisIndex])

        # exit()# 8.5 5.67

        annot = ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w") )
        annot.set_visible(False)

        ################################################################################
        import statistics
        chi2_DictOfLists = self._makeAxis_Multiple(flightsDict, constrList)

        constrDict = {}
        for constr in chi2_DictOfLists.keys():
            constrDict[constr] = {}

            σ_constr = statistics.stdev( chi2_DictOfLists[constr] )
            constrDict[constr]['Std'] = σ_constr
            constrDict[constr]['Ideal'] = min( chi2_DictOfLists[constr] )

        # NEED TO MAKE THIS PROPER
        constrDict['Price']['Weight'] = priceWeight
        constrDict['TotalFlightTime']['Weight'] = 1 - constrDict['Price']['Weight']

        chiDict = self._getChiSquared( flightsDict, constrDict )
        sortedChiList = [ (chiDict[χ2], χ2) for χ2 in sorted(chiDict, key = chiDict.get)]

        markerlist = ['*', '^', 's', 'p', 'h']
        print (delimitator)
        print (
                'Working with a {colorG} Price Weight of {wp:4.2f} {colorReset}, and a {colorG} TotalFlightTime Weight of {wtf:4.2f} {colorReset}'.format(
                wp = constrDict['Price']['Weight'],
                wtf = constrDict['TotalFlightTime']['Weight'] ,
                colorG = Fore.GREEN,
                colorReset = Style.RESET_ALL)
                )
        print (delimitator)

        for i in range(nbOfShows):

            flightCode = flightsDict['Flights'][ sortedChiList[i][1] ]['FlightCode']

            flightPrintStr = 'Flight Combination: ' + flightCode  + '\n\n' + 'At the Price of: {fPrice:8.2f} ' + '\n' + 'With an Outbound time of : {flightTimeOut:4.2f} hrs, and a Return time of : {flightTimeReturn:4.2f} hrs'

            flightPrintStr = flightPrintStr.format(
                                    fPrice = flightsDict['Flights'][ sortedChiList[i][1] ]['Price'] ,
                                    flightTimeOut = flightsDict['Flights'][ sortedChiList[i][1] ]['FlightTimeOut'],
                                    flightTimeReturn = flightsDict['Flights'][ sortedChiList[i][1] ]['FlightTimeReturn']
            )
            print ( Fore.RED +' χ²  Flight Nb ' + Style.RESET_ALL, i+1 )
            print ( flightPrintStr ,'\n\nχ^2 stats: ',
                    sortedChiList[i]
                    )
            print ()
            print (delimitator2)

            # plt.scatter( flightsDict['Flights'][ sortedChiList[i][1] ][xAxisHandle],
            #              flightsDict['Flights'][ sortedChiList[i][1] ][yAxisHandle] , marker=markerlist[i], s=100, c='black')

        # print (len(sortedChiList), len(axisDict['colorAxis']))

        def update_annot(ind):

            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos
            text = "{0}\n {1} {2} \n {3} {4} \n {5} {6}".format(
                                                  " ".join( [sortedChiList[n][1] for n in ind["ind"]] ),
                                                  " ".join( [str(axisDict['xAxis'][n]) for n in ind["ind"]] ) ,
                                                      axisLabels[0] ,
                                                  " ".join( [str(axisDict['yAxis'][n]) for n in ind["ind"]]) ,
                                                      axisLabels[1],
                                                  " ".join( [str( round(axisDict['colorAxis'][n],2) ) for n in ind["ind"]]) ,
                                                      axisLabels[2]
                                                  )
                                                  # " ".join( [names[n] for n in ind["ind"]] ),
            annot.set_text(text)
            # annot.get_bbox_patch().set_facecolor(cmap(norm(c[ind["ind"][0]])))
            annot.get_bbox_patch().set_alpha(1)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                cont, ind = sc.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)
        color_bar = fig.colorbar(sc, label = axisLabels[2])#, ticks=np.linspace(1,2,2))

        plt.xlabel(axisLabels[0])
        plt.ylabel(axisLabels[1])


        plt.show( )

        # return sortedChiList

def convertStrToDatetime(dateStr):

    dateVec = [int (dateBit) for dateBit in dateStr.split('/')]
    departDate = date( dateVec[2], dateVec[1], dateVec[0])

    return departDate

def formatDict(flightDict, keyStr):
    '''
    '''

    unformattedKeys = list (flightDict['Flights'].keys())
    for flightNb in unformattedKeys:
        flightDict['Flights'][keyStr +'-' + flightNb] = flightDict['Flights'][flightNb]


    overDetList = list(flightDict['Flights'].keys())
    for flightNb in overDetList:
        if keyStr not in flightNb:
            del flightDict['Flights'][flightNb]

    return flightDict

def findMeAHoliday(departAirp, arrivAirp, holidayDuration, betweenDate_start, betweenDate_end,
                    pmHolidayDuration=1):
    '''
    '''

    stayTimesList = []

    for holidInc in range( -pmHolidayDuration, pmHolidayDuration+1):
        stayTimesList.append(holidayDuration + holidInc)

    returnDate_Final = convertStrToDatetime(betweenDate_end)

    print(delimitator)
    print ('I want to go on Holiday for ' + Fore.BLUE + str(holidayDuration) + '±' +str(pmHolidayDuration) +' days'+ Style.RESET_ALL)
    print(delimitator)

    flightsDict = {}
    flightsDict['Flights'] = {}

    # flightsDict['FlightAttributes'] = flightsDict1 ['FlightAttributes']
    count = 0
    for stayTime in stayTimesList:

        departDate = convertStrToDatetime(betweenDate_start)
        returnDate = departDate + timedelta(days = stayTime)

        if returnDate > returnDate_Final:
            break

        print('Staying for ' + Fore.GREEN +  str(stayTime) + ' days.' + Style.RESET_ALL + ' Between ' + Fore.RED + betweenDate_start + ' ' + betweenDate_end  + Style.RESET_ALL)

        while returnDate <= returnDate_Final:

            print ('Leaving on ',departDate , '  Returning on :' , returnDate)


            wkPS = planeScraper(departAirp, arrivAirp, departDate, returnDate)
            flightsDict_partial   = wkPS._getFlightInfoReturn()

            print('Got ', len (flightsDict_partial['Flights'].keys()), ' flights.' )

            if len( list(flightsDict['Flights'].keys()) ) == 0:
                flightsDict['FlightAttributes'] = flightsDict_partial['FlightAttributes']


            # with open('Cache/CacheFile_GLA->BUH_10092018-101824.json', 'r') as inFile:
            #     flightsDict_partial  = json.load (inFile)

            flightsDict_partial = formatDict(flightsDict_partial, 'C::'+str(stayTime) + "::"+ str(departDate) + str(returnDate))
            flightsDict['Flights'].update( flightsDict_partial['Flights'] )

            print ('Total nb of flights so far :', len ( list(flightsDict['Flights'].keys() ) ))


            departDate = departDate + timedelta(days = 1)
            returnDate = departDate + timedelta(days = stayTime)
            del wkPS

            # print (wkPS.departDate, wkPS.returnDate)
            print(delimitator2)
        # print(delimitator2)
        count+=1

        # if count == 2:
        #     break
        print (delimitator)

    with open('HolidayRes-DEN.json', 'w') as outCacheFile:
        json.dump(flightsDict, outCacheFile)

    return flightsDict



    # flightsDict   = wkPS._getFlightInfoSingle()


if __name__ == '__main__':

    wkPS = planeScraper('GLA', 'BCN', '05/11/2018','11/11/2018')
    #
    # flightsDict   = wkPS._getFlightInfoReturn()
    # exit()


    # flightsDict   = wkPS._getFlightInfoSingle()

    # pp(flightsDict)

    # print (wkPS.departDate.day, wkPS.departDate.month, wkPS.departDate.year )
    # print (type (wkPS.departDate.day))

    with open('HolidayRes-DEN.json', 'r') as inFile:
        flightsDict  = json.load (inFile)


    #
    # import copy
    # flightsDict2 = copy.deepcopy(flightsDict1)
    #
    # flightsDict1 = formatDict(flightsDict1, 'Case1')
    # flightsDict2 = formatDict(flightsDict2, 'Case2')
    #
    # flightsDict = {}
    # flightsDict['Flights'] = {}
    # flightsDict['FlightAttributes'] = flightsDict1 ['FlightAttributes']
    #
    # pp(flightsDict1['Flights'])
    # pp(flightsDict2['Flights'])
    # print (len(flightsDict['Flights'].keys()))
    #
    # flightsDict['Flights'].update(flightsDict1['Flights'])
    # # flightsDict['Flights'] = {**flightsDict['Flights'], **flightsDict1['Flights']}
    #
    # print (len(flightsDict['Flights'].keys()))
    # flightsDict['Flights'].update(flightsDict2['Flights'])
    # # flightsDict['Flights'] = {**flightsDict['Flights'], **flightsDict2['Flights']}
    #
    # print (len(flightsDict['Flights'].keys()))




    # pp(flightsDict1 )
    # print ( len (flightsDict1['Flights'].keys()) )

    # unformattedKeys = list (flightsDict1['Flights'].keys())
    # for flightNb in unformattedKeys:
    #     flightsDict1['Flights']['Case1-' + flightNb] = flightsDict1['Flights'][flightNb]
    #
    #
    # overDetList = list(flightsDict1['Flights'].keys())
    # for flightNb in overDetList:
    #     if 'Case' not in flightNb:
    #         del flightsDict1['Flights'][flightNb]



    # print ( len (flightsDict1['Flights'].keys()) )

    # dictionary[new_key] = dictionary.pop(old_key)

    # with open('Cache/CacheFile_GLA->BUH_10092018-101824.json', 'r') as inFile:
    #     flightsDict2  = json.load (inFile)

    xAxisHandle = 'FlightTimeOut'
    xAxisLabel = r'Outbound Flight Time $(hrs)$'
    yAxisHandle = 'FlightTimeReturn'
    yAxisLabel = r'Return Flight Time $(hrs)$'

    colorAxisHandle = 'Price'
    colorAxisLabel = r'Price $(\textdollar)$'
    σ_Price = 1
    σ_FlightTime = 2

    # xAxisHandle = 'TotalFlightTime'
    # xAxisLabel = r'Flight Time $(hrs)$'
    # yAxisHandle = 'Price'
    # yAxisLabel = r'Price $(\textdollar)$'
    # colorAxisHandle = 'Stops'
    # colorAxisLabel = 'Stops'

    # pp (wkPS._makeAx(flightsDict, ['Price', 'FlightTime']))

    # pp(flightsDict['Flights']['Flight-O1-R33'])
    # flightList = ['O19-R56' , 'O7-R20']
    # for flightCode in flightList:
    #     pp( flightsDict['Flights']['Flight-' + flightCode]  )

    holidayDuration = 10

    cutsDict = { "Price": 800 ,
                 "FlightTimeOut" : 20,
                 "FlightTimeReturn" : 20
                }
    # flightsDict = findMeAHoliday('GLA', 'DEN', holidayDuration,  '06/02/2019','22/02/2019')


    wkPS.plotFlights( flightsDict, xAxisHandle, yAxisHandle, colorAxisHandle, [xAxisLabel, yAxisLabel, colorAxisLabel] , cutsDict, priceWeight = 0.3)
