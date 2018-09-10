import json
import requests
from lxml import html
from collections import OrderedDict
import argparse
from  pprint import pprint as pp
import random

from matplotlib.pyplot import colorbar
import matplotlib.pyplot as plt

from datetime import *
import os


nbrTerminalRows, nbrTerminalCols = os.popen('stty size', 'r').read().split()
nbrTerminalRows = int(nbrTerminalRows)
nbrTerminalCols = int(nbrTerminalCols)
delimitator = '\n' + '▓' * nbrTerminalCols + '\n'
FNULL = open(os.devnull, 'w')

class planeScraper:
    '''
        ADD DOCUMENTATION

    '''
    # REQUEST_ID_REGEX = r"data-leg-natural-key=\"(\w+)\">"

    def __init__(self, departAirp, arrivAirp, departDate, returnDate = None):
        '''
        '''

        # Maybe introduce some cleaning / formatting tool here?
        self.departAirp = departAirp
        self.arrivAirp = arrivAirp

        # ADD CROSSCHECK WITH AIRPORT DATABASE, also introduce location/iata code mathcer

        dateVec = [int (dateBit) for dateBit in departDate.split('/')]
        self.departDate = date( dateVec[2], dateVec[1], dateVec[0])

        if returnDate != None :
            dateVec2 = [int (dateBit) for dateBit in returnDate.split('/')]
            self.returnDate = date( dateVec2[2], dateVec2[1], dateVec2[0])
        else:
            self.returnDate = None

        print('Got Flight details!')
        if returnDate:
            print ('Number of Days: ', self.returnDate - self.departDate)

    def _makeFlightsDictHead(self, flightDataDict):
        '''
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

        # {
        #                             'TimeDelta' : auxTime.total_seconds(),
        #                             'Formatted' : str(auxTime) }

        flightCodeStr = ''
        for stopNb in range ( len( flightDataDict['legs'][flightID]['timeline'] ) ):

            if 'carrier' in flightDataDict['legs'][flightID]['timeline'][stopNb].keys():

                flightCodeStr += \
                    ( flightDataDict['legs'][flightID]['timeline'][stopNb]['carrier']['airlineCode'] +             flightDataDict['legs'][flightID]['timeline'][stopNb]['carrier']['flightNumber'] )

                flightCodeStr += '$\\rightarrow$' #Modify below if replacing →
        flightInfo['FlightCode'] = flightCodeStr[:-13]


        # pp (flightDataDict['legs'][flightID]['timeline'])
        # print ('Flight-'+str(flightCount+1))
        # pp (flightInfo)

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

        print(expediaURL)


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

    def _getFlightInfoReturn(self, writeToCache = False):
        '''
            To be called if we have a return flight
        '''
        expediaURL = "https://www.expedia.com/Flights-Search?flight-type=on&starDate={0}%2F{1}%2F{2}&endDate={3}%2F{4}%2F{5}&mode=search&trip=roundtrip&leg1=from%3A{6}%2Cto%3A{7}%2Cdeparture%3A{0}%2F{1}%2F{2}TANYT&leg2=from%3A{7}%2Cto%3A{6}%2Cdeparture%3A{3}%2F{4}%2F{5}TANYT&passengers=adults%3A1%2Cchildren%3A0%2Cseniors%3A0%2Cinfantinlap%3AY&options=cabinclass%3Aeconomy&mode=search&origref=www.expedia.com".format(
            str(wkPS.departDate.month), str(wkPS.departDate.day), str(wkPS.departDate.year),
            str(wkPS.returnDate.month), str(wkPS.returnDate.day), str(wkPS.returnDate.year),
            self.departAirp, self.arrivAirp )



        expediaResp = requests.get(expediaURL)
        parser = html.fromstring(expediaResp.text)
        json_data_xpath = parser.xpath("//script[@id='cachedResultsJson']//text()")

        raw_json = json.loads(json_data_xpath[0] if json_data_xpath else '')
        flightDataDictOutBound = json.loads(raw_json["content"])

        from pattern.web import Element

        el1 = Element(expediaResp.content)
        departure_request_id = el1("div#originalContinuationId")[0].content

        flightsDict = self._makeFlightsDictHead( flightDataDictOutBound )

        # Will have to loop over outbounds here via list(flightDataDictOutBound['legs'].keys())[0]; REplace [0] with flightNb

        for  flightNb_Outbound, flightID_Outbound in enumerate(flightDataDictOutBound['legs'].keys()):

            # if flightID_Outbound != '42feffd1743e8ea1afecec3a04d7b294':
            #     continue
            # else:

            print(flightID_Outbound, flightNb_Outbound)


            flightInfo_Out = self._makeFlightInfoDict(flightDataDictOutBound, flightID_Outbound, 'Outbound')

            json_url = "https://www.expedia.com/Flight-Search-Paging?c={DEPT_ID}&is=1" \
            "&fl0={ARRV_ID}&sp=asc&cz=200&cn=0&ul=1"

            json_url = json_url.format(
                DEPT_ID=departure_request_id,
                ARRV_ID=list(flightDataDictOutBound['legs'].keys())[flightNb_Outbound]
            )
            # print(json_url)

            get_request = requests.get(json_url)
            parser = html.fromstring(get_request.text)
            flightDataDictReturn = get_request.json()['content']

            # pp(flightDataDictReturn['legs'])

            for  flightNb_Return, flightID_Return in enumerate(flightDataDictReturn['legs'].keys()):
                # print(flightID_Return, flightNb_Return)
                # pp(flightDataDictReturn['legs'][flightID_Return]['price'])

                if flightID_Outbound == flightID_Return :
                    print(flightID_Outbound, flightID_Return)
                    continue

                # if flightID_Return == 'd96ed0d1259afc7d0bbfd46a23b71f02' or flightID_Return == '5db475cc4090939bcfd18ba5f8097b3a':
                #     # continue
                #     # print ('____')
                #
                #     # pp(flightDataDictReturn['legs'][flightID_Return]['price'])
                #     print(delimitator)
                # else:
                #     continue

                # exit()
                # pp (list(flightDataDictReturn['index'] ))

                flightInfo_Return = self._makeFlightInfoDict(flightDataDictReturn, flightID_Return, 'Return')
                # print(flightInfo_Return['Price'], ' for the Return Trip, with an outbound: ', flightInfo_Out['Price'])
                # pp (flightInfo_Out)
                # pp (flightInfo_Return)


                flightInfo = self._makeReturnFlightFromDicts(flightInfo_Out, flightInfo_Return)

                # pp (flightInfo)
                # if flightNb_Return == 2:
                #     exit()
                flightsDict['Flights']['Flight-O'+str(flightNb_Outbound+1) + '-R' + str(flightNb_Return+1) ] = flightInfo

                # pp (flightInfo)

                del(flightInfo)
                # exit()

            print(delimitator)

            # if flightNb_Outbound == 3:

        self._writeToCache(flightsDict)

        return flightsDict
            # exit()

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
        '''

        xAxis = []
        yAxis = []
        colorAxis = []
        labelAxis = []

        for flightNb in flightsDict['Flights'].keys():
            for axis, axisHandle in zip([xAxis, yAxis, colorAxis, labelAxis], [ xAxisHandle, yAxisHandle, colorAxisHandle, 'FlightCode']):
                axis.append( flightsDict['Flights'][flightNb][axisHandle] )

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
                chi2 =  constrStdevs[chi2Constr]['Weight'] * ( (flightsDict['Flights'][flightNb][chi2Constr] - constrStdevs[chi2Constr]['Ideal'])**2) /       ((constrStdevs[chi2Constr]['Std'])**2)
                flightChi2 += chi2
                # print (flightNb, chi2Constr,  flightsDict['Flights'][flightNb][chi2Constr], constrStdevs[chi2Constr])

            chi2Dict[flightNb] = round(flightChi2, 2)
            # print (delimitator)

        return chi2Dict

    def plotFlights(self, flightsDict, xAxisHandle, yAxisHandle, colorAxisHandle, axisLabels, colorMap = 'RdBu_r', constrList = ['Price', 'TotalFlightTime'],  ):
        '''
        '''
        plt.rc('font', size = 40)
        plt.rc('text', usetex=True)
        fig,ax = plt.subplots(figsize=(20, 7))

        axisDict = self._makeAxisFromDict(flightsDict, xAxisHandle, yAxisHandle, colorAxisHandle)

        # matplotlib labels here !!
        names = axisDict['labelAxis']

        sc = plt.scatter ( axisDict['xAxis'], axisDict['yAxis'],
                                    c = axisDict['colorAxis'] ,
                                    cmap = colorMap    )


        annot = ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w") )
        annot.set_visible(False)

        def update_annot(ind):

            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos
            text = "{0}\n {1} {2} \n {3} {4} \n {5} {6}".format(
                                                  " ".join( ['Flight ' + str(n) for n in ind["ind"]] ),
                                                  " ".join( [str(axisDict['xAxis'][n]) for n in ind["ind"]] ) ,
                                                      axisLabels[0] ,
                                                  " ".join( [str(axisDict['yAxis'][n]) for n in ind["ind"]]) ,
                                                      axisLabels[1],
                                                  " ".join( [str(axisDict['colorAxis'][n]) for n in ind["ind"]]) ,
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

        import numpy as np
        color_bar = fig.colorbar(sc, label = axisLabels[2])#, ticks=np.linspace(1,2,2))

        import statistics
        chi2_DictOfLists = self._makeAxis_Multiple(flightsDict, constrList)

        constrDict = {}
        for constr in chi2_DictOfLists.keys():
            constrDict[constr] = {}
            σ_constr = round (statistics.stdev( chi2_DictOfLists[constr] ), 2)
            constrDict[constr]['Std'] = σ_constr
            constrDict[constr]['Ideal'] = min( chi2_DictOfLists[constr] )

        # NEED TO MAKE THIS PROPER
        constrDict['Price']['Weight'] = 0.9
        constrDict['TotalFlightTime']['Weight'] = 1 - 0.9

        chiDict = self._getChiSquared(flightsDict, constrDict )
        sortedChiList = [ (chiDict[χ2], χ2) for χ2 in sorted(chiDict, key = chiDict.get)]

        markerlist = ['*',  '^', 's', 'p', 'h']

        print ('Working with a Price Weight of {1}, and a TotalFlightTime Weight of '.format(constrDict['Price']['Weight'], constrDict['TotalFlightTime']['Weight'] ) )
        print (delimitator)

        for i in range(5):
            print ( flightsDict['Flights'][ sortedChiList[i][1] ]['FlightCode'] ,
                    flightsDict['Flights'][ sortedChiList[i][1] ]['Price'] ,
                    flightsDict['Flights'][ sortedChiList[i][1] ]['FlightTimeOut'],
                    flightsDict['Flights'][ sortedChiList[i][1] ]['FlightTimeReturn'],

                    sortedChiList[i])

            plt.scatter( flightsDict['Flights'][ sortedChiList[i][1] ][xAxisHandle],
                         flightsDict['Flights'][ sortedChiList[i][1] ][yAxisHandle] , marker=markerlist[i], s=100, c='black')

        plt.xlabel(axisLabels[0])
        plt.ylabel(axisLabels[1])


        plt.show()



if __name__ == '__main__':

    wkPS = planeScraper('GLA', 'BUH', '04/11/2018','11/11/2018')

    # flightsDict   = wkPS._getFlightInfoReturn()
    # pp(flightsDict)
    # print (wkPS.departDate.day, wkPS.departDate.month, wkPS.departDate.year )
    # print (type (wkPS.departDate.day))
    with open('Cache/CacheFile_GLA->BUH_10092018-101824.json', 'r') as inFile:
        flightsDict  = json.load (inFile)

    xAxisHandle = 'FlightTimeOut'
    xAxisLabel = 'hrs'
    yAxisHandle = 'FlightTimeReturn'
    yAxisLabel = 'hrs'

    colorAxisHandle = 'Price'
    colorAxisLabel = 'USD'
    σ_Price = 1
    σ_FlightTime = 2

    # pp (wkPS._makeAx(flightsDict, ['Price', 'FlightTime']))



    wkPS.plotFlights( flightsDict, xAxisHandle, yAxisHandle, colorAxisHandle, [xAxisLabel, yAxisLabel, colorAxisLabel] )
