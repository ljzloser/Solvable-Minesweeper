import QtQuick 2.15
import QtCharts 2.3

/**
 * 趋势折线图
 *
 * 显示最近 N 局的 rtime 和 3BV/s 趋势
 */

ChartView {
    id: chartView
    title: "趋势"
    titleColor: "#cdd6f4"
    titleFont.pixelSize: 14
    backgroundColor: "#313244"
    legend.visible: true
    legend.color: "#cdd6f4"
    legend.labelColor: "#cdd6f4"
    antialiasing: true
    margins.top: 30
    margins.bottom: 20
    margins.left: 10
    margins.right: 10

    property var trendData: []

    function refresh() {
        var json
        if (root.currentLevel === -1) {
            json = JSON.parse(bridge.getTrend(200))
        } else {
            json = JSON.parse(bridge.getTrendByLevel(root.currentLevel, 200))
        }

        trendData = json
        updateChart()
    }

    function updateChart() {
        // 清除旧系列
        chartView.removeAllSeries()

        var axisX = chartView.axisX()
        var axisYLeft = chartView.axisY()
        var axisYRight = null

        if (trendData.length === 0) {
            return
        }

        // 反转数据使最新在右
        var data = trendData.slice().reverse()
        var len = data.length

        // rtime 系列
        var rtimeSeries = chartView.createSeries(ChartView.SeriesTypeLine, "rtime (s)")
        rtimeSeries.color = "#89b4fa"
        rtimeSeries.width = 2

        // 3BV/s 系列
        var bbbvsSeries = chartView.createSeries(ChartView.SeriesTypeLine, "3BV/s")
        bbbvsSeries.color = "#a6e3a1"
        bbbvsSeries.width = 2

        var maxRtime = 0
        var maxBbbvs = 0

        for (var i = 0; i < len; i++) {
            var rtime = parseFloat(data[i].rtime) || 0
            var bbbvs = parseFloat(data[i].bbbv_s) || 0
            var isWin = data[i].game_state === root.enums.gameState.win

            rtimeSeries.append(i, rtime)
            bbbvsSeries.append(i, bbbvs)

            if (rtime > maxRtime) maxRtime = rtime
            if (bbbvs > maxBbbvs) maxBbbvs = bbbvs
        }

        // X 轴
        var axisXObj = Qt.createQmlObject('import QtCharts 2.3; ValueAxis {}', chartView)
        axisXObj.min = 0
        axisXObj.max = Math.max(len - 1, 1)
        axisXObj.labelsColor = "#a6adc8"
        axisXObj.gridVisible = false
        axisXObj.visible = false
        chartView.setAxisX(axisXObj, rtimeSeries)
        chartView.setAxisX(axisXObj, bbbvsSeries)

        // Y 左轴 (rtime)
        var axisYLeftObj = Qt.createQmlObject('import QtCharts 2.3; ValueAxis {}', chartView)
        axisYLeftObj.min = 0
        axisYLeftObj.max = Math.max(maxRtime * 1.1, 1)
        axisYLeftObj.labelsColor = "#89b4fa"
        axisYLeftObj.titleText = "rtime (s)"
        axisYLeftObj.gridVisible = true
        axisYLeftObj.gridLineColor = "#45475a"
        chartView.setAxisY(axisYLeftObj, rtimeSeries)

        // Y 右轴 (3BV/s)
        var axisYRightObj = Qt.createQmlObject('import QtCharts 2.3; ValueAxis {}', chartView)
        axisYRightObj.min = 0
        axisYRightObj.max = Math.max(maxBbbvs * 1.1, 1)
        axisYRightObj.labelsColor = "#a6e3a1"
        axisYRightObj.titleText = "3BV/s"
        axisYRightObj.gridVisible = false
        chartView.setAxisY(axisYRightObj, bbbvsSeries)
    }
}
