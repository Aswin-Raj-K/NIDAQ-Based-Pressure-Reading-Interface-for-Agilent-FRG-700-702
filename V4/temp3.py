import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGraphicsRectItem, QGraphicsSimpleTextItem
from PyQt5.QtGui import QBrush, QColor
import pyqtgraph as pg

class CustomLegendItem(QGraphicsRectItem):
    def __init__(self, color, label):
        super().__init__(0, 0, 10, 10)
        self.setBrush(QBrush(color))
        self.label = label

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Plot with Custom Legend Example")
        self.resize(800, 600)

        # Create the main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        # Create the PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)

        # Add PlotDataItems to the PlotWidget
        self.plot1 = self.plot_widget.plot([1, 2, 3], [4, 5, 6], pen='r', name="Plot 1")
        self.plot2 = self.plot_widget.plot([1, 2, 3], [6, 5, 4], pen='g', name="Plot 2")
        self.plot3 = self.plot_widget.plot([1, 2, 3], [5, 6, 4], pen='b', name="Plot 3")

        # Create and add the LegendItem
        self.legend = pg.LegendItem((80, 60), offset=(30, 30))
        self.legend.setParentItem(self.plot_widget.graphicsItem())

        # Add custom legend entries
        self.add_custom_legend_entry("Plot 1", QColor('red'))
        self.add_custom_legend_entry("Plot 2", QColor('green'))
        self.add_custom_legend_entry("Plot 3", QColor('blue'))

    def add_custom_legend_entry(self, name, color):
        # Create custom legend item
        custom_item = CustomLegendItem(color, name)

        # Create a text item for the legend label
        text_item = QGraphicsSimpleTextItem(name)

        # Add the custom item to the legend
        self.legend.addItem(custom_item, text_item)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
