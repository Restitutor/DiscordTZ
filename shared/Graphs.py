import copy
import random
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy
from matplotlib import pyplot, dates

from database.stats.StatsData import StatsData


async def packetFailSuccessGraph(startTimestamp: datetime | None, endTimestamp: datetime | None) -> None:
    dataset: list[tuple[datetime, StatsData]] = await StatsData.loadBulk(startTimestamp, endTimestamp)

    packetFailCounts = numpy.array([data[1].failedRequestCount for data in dataset])
    packetSuccessCounts = numpy.array([data[1].successfulRequestCount for data in dataset])

    pyplot.figure(figsize=(16, 9))

    timePoints = numpy.array([data[0].replace(tzinfo=ZoneInfo("Europe/Prague")) for data in copy.deepcopy(dataset)])

    pyplot.fill_between(timePoints, 0, packetFailCounts, color="red", alpha=0.5, label="Received Packet Errors")
    pyplot.plot(timePoints, packetFailCounts, color="red")
    pyplot.fill_between(timePoints, 0, packetSuccessCounts, color="green", alpha=0.5, label="Received Packets Successes", interpolate=True)
    pyplot.plot(timePoints, packetSuccessCounts, color="green")

    topIndexes = numpy.argsort(packetFailCounts)[-3:]
    for idx in topIndexes:
        x = timePoints[idx]
        y = packetFailCounts[idx]
        stats = dataset[idx][1]

        topCountry = max(stats.requestCountries.items(), key=lambda item: item[1])[0]
        countryInfo = f"Main Source: {topCountry}"

        pyplot.annotate(
            f"{countryInfo}",
            xy=(x, y), xytext=(0, 15),
            textcoords='offset points',
            arrowprops=dict(facecolor='red', shrink=0.05, width=1, headwidth=6),
            fontsize=9, color='darkred',
            ha='center', va='bottom'
        )

    pyplot.ylabel("# of Requests")
    pyplot.title("Fail and Success Counts Over Time")
    pyplot.legend()
    pyplot.grid(True)


    ax = pyplot.gca()
    ax.set_ylabel("# of Requests")
    ax.set_title("Fail and Success Counts Over Time")
    ax.legend()
    ax.grid(True)
    ax.margins(y=0.02)

    locator = dates.AutoDateLocator()
    formatter = dates.AutoDateFormatter("%H:%M", tz=ZoneInfo("Europe/Prague"))
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.margins(y=0.02)

    pyplot.setp(ax.get_xticklabels(), rotation=45, ha="right")

    pyplot.savefig("stats/packetFailSuccessGraph.png", dpi=600, bbox_inches="tight")
    pyplot.close()

async def packetTypesPieChart(startTimestamp: datetime | None, endTimestamp: datetime | None):
    dataset: list[tuple[datetime, StatsData]] = await StatsData.loadBulk(startTimestamp, endTimestamp)

    summedUpDict = defaultdict(int)
    summedUpDict["INVALID"] = sum([data[1].failedRequestCount for data in dataset])

    for data in dataset:
        for k, v in data[1].establishedKnownRequestTypes.items():
            summedUpDict[k] += v

    summedUpDict = dict(sorted(summedUpDict.items(), key=lambda item: item[1], reverse=True))

    labels = list(summedUpDict.keys())
    sizes = list(summedUpDict.values())
    colors = ['red' if label == 'INVALID' else "#{:06x}".format(random.randint(0x100000, 0xFFFFFF)) for label in labels]

    pyplot.figure(figsize=(8, 8))
    pyplot.pie(sizes, labels=labels, colors=colors, autopct='%1.2f%%', startangle=90, wedgeprops={'edgecolor': 'black'})

    pyplot.legend()
    pyplot.title("Distribution of received requests")

    pyplot.savefig("stats/packetTypesPieChart.png", dpi=600)
    pyplot.close()
