import QtQuick 2.15
import QtCharts 2.3

/**
 * 难度分布饼图
 */

ChartView {
    id: chartView
    title: "难度分布"
    titleColor: "#cdd6f4"
    titleFont.pixelSize: 14
    backgroundColor: "#313244"
    legend.visible: true
    legend.color: "#cdd6f4"
    legend.labelColor: "#cdd6f4"
    antialiasing: true
    margins.top: 30
    margins.bottom: 10
    margins.left: 10
    margins.right: 10

    property var pieData: []

    function refresh() {
        var json = JSON.parse(bridge.getLevelDistribution())
        pieData = json
        updateChart()
    }

    function updateChart() {
        chartView.removeAllSeries()

        if (pieData.length === 0) {
            return
        }

        var pieSeries = chartView.createSeries(ChartView.SeriesTypePieSeries, "")
        pieSeries.holeVisible = true  // 环形图
        pieSeries.holeSize = 0.4

        var levelColors = {
            3: "#89b4fa",  // 初级 - 蓝
            4: "#a6e3a1",  // 中级 - 绿
            5: "#f38ba8",  // 高级 - 红
            6: "#fab387",  // 自定义 - 橙
        }

        var levelLabels = {
            3: "初级",
            4: "中级",
            5: "高级",
            6: "自定义",
        }

        var total = 0
        for (var i = 0; i < pieData.length; i++) {
            total += pieData[i].count
        }

        for (var i = 0; i < pieData.length; i++) {
            var level = pieData[i].level
            var count = pieData[i].count
            var slice = pieSeries.append(
                levelLabels[level] || ("Level " + level),
                count
            )
            if (!slice) continue
            slice.color = levelColors[level] || "#cdd6f4"
            slice.borderColor = "#1e1e2e"
            slice.borderWidth = 2
            slice.labelVisible = true
            slice.labelColor = "#cdd6f4"
            slice.labelFont.pixelSize = 11
            slice.labelPosition = 1  // LabelOutside = 1

            // 百分比标签
            var pct = total > 0 ? (count / total * 100).toFixed(1) : "0"
            slice.label = (levelLabels[level] || ("Level " + level)) + " " + pct + "%"
        }
    }
}
