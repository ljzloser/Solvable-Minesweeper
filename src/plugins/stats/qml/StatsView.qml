import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import QtCharts 2.3

/**
 * 统计插件主视图
 *
 * 布局：
 * ┌─────────────────────────────────────────┐
 * │  [筛选栏]  难度: [ComboBox]  [刷新按钮] │
 * ├──────────────┬──────────────────────────┤
 * │  汇总卡片    │   趋势折线图             │
 * │  总局数      │                          │
 * │  胜率        │                          │
 * │  均时        │                          │
 * │  最佳        │                          │
 * ├──────────────┼──────────────────────────┤
 * │  难度饼图    │   时间分布柱状图         │
 * │              │                          │
 * └──────────────┴──────────────────────────┘
 */

Rectangle {
    id: root
    color: "#1e1e2e"

    // 当前筛选难度 (-1 = 全部)
    property int currentLevel: -1
    property var levelNames: ({})
    property var summaryData: ({})
    property var enums: ({})  // 从 bridge 获取的枚举值

    // 延迟首次刷新，等 bridge 就绪
    Timer {
        id: initTimer
        interval: 500
        running: true
        repeat: false
        onTriggered: refreshAll()
    }

    // 监听 bridge 数据变化
    Connections {
        target: bridge
        function onDataChanged() {
            refreshAll();
        }
    }

    function refreshAll() {
        var names = JSON.parse(bridge.getLevelNames());
        root.levelNames = names;

        root.enums = JSON.parse(bridge.getEnumValues());

        var summary;
        if (currentLevel === -1) {
            summary = JSON.parse(bridge.getSummary());
        } else {
            summary = JSON.parse(bridge.getSummaryByLevel(currentLevel));
        }
        root.summaryData = summary || {};

        trendChart.refresh();
        distChart.refresh();
        pieChart.refresh();
    }

    // ── 主布局 ──────────────────────────────────────────

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // ── 筛选栏 ──
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Label {
                text: "难度:"
                color: "#cdd6f4"
                font.pixelSize: 14
            }

            ComboBox {
                id: levelCombo
                model: ["全部", "初级", "中级", "高级", "自定义"]
                currentIndex: 0
                onActivated: {
                    // -1=全部, 然后按 enums.level 中的值
                    var levelValues = [enums.level.beginner, enums.level.intermediate, enums.level.expert, enums.level.custom];
                    currentLevel = currentIndex === 0 ? -1 : levelValues[currentIndex - 1];
                    refreshAll();
                }

                background: Rectangle {
                    color: "#313244"
                    radius: 4
                    border.color: "#45475a"
                }
                contentItem: Text {
                    text: levelCombo.displayText
                    color: "#cdd6f4"
                    font.pixelSize: 14
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 8
                }
                delegate: ItemDelegate {
                    width: levelCombo.width
                    contentItem: Text {
                        text: modelData
                        color: "#cdd6f4"
                        font.pixelSize: 14
                    }
                    background: Rectangle {
                        color: highlighted ? "#45475a" : "#313244"
                    }
                    highlighted: levelCombo.highlightedIndex === index
                }
                popup: Popup {
                    y: levelCombo.height
                    width: levelCombo.width
                    implicitHeight: contentItem.implicitHeight
                    padding: 1

                    contentItem: ListView {
                        clip: true
                        implicitHeight: contentHeight
                        model: levelCombo.popup.visible ? levelCombo.delegateModel : null
                        currentIndex: levelCombo.highlightedIndex
                    }

                    background: Rectangle {
                        color: "#313244"
                        border.color: "#45475a"
                        radius: 4
                    }
                }
            }

            Button {
                text: "刷新"
                onClicked: refreshAll()

                background: Rectangle {
                    color: parent.pressed ? "#45475a" : "#313244"
                    radius: 4
                    border.color: "#585b70"
                }
                contentItem: Text {
                    text: parent.text
                    color: "#cdd6f4"
                    font.pixelSize: 14
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Item {
                Layout.fillWidth: true
            }
        }

        // ── 上半区：汇总卡片 + 趋势图 ──
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 200
            spacing: 12

            // 汇总卡片
            ColumnLayout {
                Layout.preferredWidth: 180
                Layout.fillHeight: true
                spacing: 8

                SummaryCard {
                    Layout.fillWidth: true
                    title: "总局数"
                    value: (root.summaryData && root.summaryData.total) || 0
                    icon: "\u{1F3AE}"
                }
                SummaryCard {
                    Layout.fillWidth: true
                    title: "胜局"
                    value: (root.summaryData && root.summaryData.wins) || 0
                    icon: "\u{1F3C6}"
                }
                SummaryCard {
                    Layout.fillWidth: true
                    title: "胜率"
                    value: root.summaryData && root.summaryData.total > 0 ? ((root.summaryData.wins || 0) / root.summaryData.total * 100).toFixed(1) + "%" : "0%"
                    icon: "\u{1F4C8}"
                }
                SummaryCard {
                    Layout.fillWidth: true
                    title: "均时"
                    value: root.summaryData && root.summaryData.avg_win_time ? root.summaryData.avg_win_time.toFixed(2) + "s" : "-"
                    icon: "\u{23F1}"
                }
                SummaryCard {
                    Layout.fillWidth: true
                    title: "最佳"
                    value: root.summaryData && root.summaryData.best_time ? root.summaryData.best_time.toFixed(2) + "s" : "-"
                    icon: "\u{2B50}"
                }
                SummaryCard {
                    Layout.fillWidth: true
                    title: "3BV/s"
                    value: root.summaryData && root.summaryData.avg_3bvs ? root.summaryData.avg_3bvs.toFixed(2) : "-"
                    icon: "\u{26A1}"
                }
            }

            // 趋势折线图
            TrendChart {
                id: trendChart
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }

        // ── 下半区：饼图 + 分布图 ──
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 200
            spacing: 12

            // 难度饼图
            PieLevelChart {
                id: pieChart
                Layout.preferredWidth: 280
                Layout.fillHeight: true
            }

            // 时间分布柱状图
            DistributionChart {
                id: distChart
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }

    // ── 汇总卡片组件 ────────────────────────────────────

    component SummaryCard: Rectangle {
        property string title: ""
        property var value: 0
        property string icon: ""

        color: "#313244"
        radius: 8
        implicitHeight: 48

        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 8

            Text {
                text: icon
                font.pixelSize: 20
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: title
                    color: "#a6adc8"
                    font.pixelSize: 11
                }
                Text {
                    text: String(value)
                    color: "#cdd6f4"
                    font.pixelSize: 16
                    font.bold: true
                }
            }
        }
    }
}
