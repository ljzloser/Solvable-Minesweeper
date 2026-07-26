import QtQuick 2.15
import QtCharts 2.3

/**
 * 时间分布柱状图
 *
 * 显示完成时间的频率分布
 */

ChartView {
    id: chartView
    title: "时间分布"
    titleColor: "#cdd6f4"
    titleFont.pixelSize: 14
    backgroundColor: "#313244"
    legend.visible: false
    antialiasing: true
    margins.top: 30
    margins.bottom: 20
    margins.left: 10
    margins.right: 10

    property var distData: []

    function refresh() {
        var json
        if (root.currentLevel === -1) {
            json = JSON.parse(bridge.getTimeDistribution())
        } else {
            json = JSON.parse(bridge.getTimeDistributionByLevel(root.currentLevel))
        }

        distData = json
        updateChart()
    }

    function updateChart() {
        chartView.removeAllSeries()

        if (distData.length === 0) {
            return
        }

        var barSeries = chartView.createSeries(ChartView.SeriesTypeBarSeries, "")

        var values = []
        var categories = []
        var maxCount = 0

        for (var i = 0; i < distData.length; i++) {
            var bucket = parseFloat(distData[i].time_bucket) || 0
            var count = parseInt(distData[i].count) || 0
            values.push(count)
            categories.push(Math.round(bucket) + "s")
            if (count > maxCount) maxCount = count
        }

        barSeries.append("局数", values)
        barSeries.barWidth = 0.8

        // X 轴
        var axisXObj = Qt.createQmlObject('import QtCharts 2.3; BarCategoryAxis {}', chartView)
        axisXObj.categories = categories
        axisXObj.labelsColor = "#a6adc8"
        axisXObj.labelsFont.pixelSize = 10
        axisXObj.gridVisible = false
        chartView.setAxisX(axisXObj, barSeries)

        // Y 轴
        var axisYObj = Qt.createQmlObject('import QtCharts 2.3; ValueAxis {}', chartView)
        axisYObj.min = 0
        axisYObj.max = Math.max(maxCount * 1.1, 1)
        axisYObj.labelsColor = "#a6adc8"
        axisYObj.gridVisible = true
        axisYObj.gridLineColor = "#45475a"
        chartView.setAxisY(axisYObj, barSeries)
    }
}
