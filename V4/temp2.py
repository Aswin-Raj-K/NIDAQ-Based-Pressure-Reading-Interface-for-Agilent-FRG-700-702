import sys
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QMenuBar, QAction, QSplitter
from PyQt5.QtCore import Qt

class GraphWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Pressure Graph")
        self.setGeometry(100, 100, 1200, 800)

        # Create a central widget and set the layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        # Create a menu bar
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        # Add a menu and action to split the graph
        self.view_menu = self.menu_bar.addMenu("View")
        self.split_action = QAction("Split into 3 Graphs", self)
        self.split_action.triggered.connect(self.split_graphs)
        self.view_menu.addAction(self.split_action)

        # Create a layout for the plot widgets
        self.plot_layout = QVBoxLayout()
        self.main_layout.addLayout(self.plot_layout)

        # Create the initial plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("Pressure", color="black", size="15pt")
        self.plot_layout.addWidget(self.plot_widget)

        self.plot_widgets = [self.plot_widget]  # Keep track of plot widgets

    def ylabel(self, ylabel):
        for widget in self.plot_widgets:
            widget.setLabel('left', ylabel, color='black', size='12pt')

    def xlabel(self, xlabel="Time (min)"):
        for widget in self.plot_widgets:
            widget.setLabel('bottom', xlabel, color='black', size='12pt')

    def plot_data(self, x=None, y=None, pen=None, symbol='o', symbolSize=8, symbolBrush=None):
        if x is None or y is None:
            x = np.linspace(0, 10, 100)
            y = np.sin(x)

        if pen is None:
            pen = pg.mkPen(color='r', width=2)

        if symbolBrush is None:
            symbolBrush = pg.mkBrush('r')

        # Plot the data on the first plot widget
        self.plot_widgets[0].plot(x, y, pen=pen, symbol=symbol, symbolSize=symbolSize, symbolBrush=symbolBrush)

    def clearGraph(self):
        for widget in self.plot_widgets:
            widget.clear()

    def closeEvent(self, event):
        if hasattr(self.parent(), "onGraphClosed"):
            self.parent().onGraphClosed()
        super().closeEvent(event)

    def split_graphs(self):
        # Clear the existing layout
        for i in reversed(range(self.plot_layout.count())):
            self.plot_layout.itemAt(i).widget().setParent(None)

        # Create a QSplitter to hold multiple plot widgets
        self.splitter = QSplitter(Qt.Vertical)

        self.plot_widgets = []

        # Create and add three new plot widgets
        for i in range(3):
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('w')
            plot_widget.setTitle(f"Pressure {i + 1}", color="black", size="15pt")

            self.splitter.addWidget(plot_widget)
            self.plot_widgets.append(plot_widget)

        self.plot_layout.addWidget(self.splitter)

        # Set the labels for each plot widget
        self.ylabel('Pressure (Pa)')
        self.xlabel('Time (min)')

        # Plot some sample data in each plot widget
        x = np.linspace(0, 10, 100)
        y1 = np.sin(x)
        y2 = 2 * np.sin(x)
        y3 = 0.5 * np.sin(x)

        self.plot_widgets[0].plot(x, y1, pen=pg.mkPen(color='r', width=2), symbolBrush=pg.mkBrush('r'))
        self.plot_widgets[1].plot(x, y2, pen=pg.mkPen(color='g', width=2), symbolBrush=pg.mkBrush('g'))
        self.plot_widgets[2].plot(x, y3, pen=pg.mkPen(color='b', width=2), symbolBrush=pg.mkBrush('b'))

def main():
    app = QApplication(sys.argv)

    window = GraphWindow()
    window.ylabel('Pressure (Pa)')
    window.xlabel('Time (min)')

    # Plot initial data
    x1 = np.linspace(0, 10, 100)
    y1 = np.sin(x1)
    window.plot_data(x1, y1, pen=pg.mkPen(color='r', width=2), symbolBrush=pg.mkBrush('r'))

    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
