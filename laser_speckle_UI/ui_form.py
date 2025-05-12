# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QSizePolicy, QSlider,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(1000, 700)
        self.horizontalLayout_2 = QHBoxLayout(Widget)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(12)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.groupBox = QGroupBox(Widget)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setMinimumSize(QSize(200, 0))
        font = QFont()
        font.setPointSize(12)
        self.groupBox.setFont(font)
        self.verticalLayout_8 = QVBoxLayout(self.groupBox)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.verticalLayout_8.addWidget(self.label)

        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font)
        self.label_2.setWordWrap(True)

        self.verticalLayout_8.addWidget(self.label_2)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.label_15 = QLabel(self.groupBox)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setFont(font)

        self.verticalLayout_6.addWidget(self.label_15)

        self.horizontalSlider = QSlider(self.groupBox)
        self.horizontalSlider.setObjectName(u"horizontalSlider")
        self.horizontalSlider.setOrientation(Qt.Orientation.Horizontal)

        self.verticalLayout_6.addWidget(self.horizontalSlider)


        self.verticalLayout_8.addLayout(self.verticalLayout_6)

        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.load_button = QPushButton(self.groupBox)
        self.load_button.setObjectName(u"load_button")
        self.load_button.setMinimumSize(QSize(0, 40))
        self.load_button.setFont(font)

        self.verticalLayout_7.addWidget(self.load_button)

        self.reset_roi_button = QPushButton(self.groupBox)
        self.reset_roi_button.setObjectName(u"reset_roi_button")
        self.reset_roi_button.setMinimumSize(QSize(0, 40))
        self.reset_roi_button.setFont(font)

        self.verticalLayout_7.addWidget(self.reset_roi_button)


        self.verticalLayout_8.addLayout(self.verticalLayout_7)

        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setMinimumSize(QSize(0, 120))
        self.label_3.setFont(font)

        self.verticalLayout_8.addWidget(self.label_3)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer)


        self.horizontalLayout.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(Widget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setMinimumSize(QSize(200, 0))
        self.groupBox_2.setFont(font)
        self.verticalLayout_9 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.label_9 = QLabel(self.groupBox_2)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setFont(font)

        self.verticalLayout_9.addWidget(self.label_9)

        self.label_10 = QLabel(self.groupBox_2)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setFont(font)
        self.label_10.setWordWrap(True)

        self.verticalLayout_9.addWidget(self.label_10)

        self.label_11 = QLabel(self.groupBox_2)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setFont(font)
        self.label_11.setWordWrap(True)

        self.verticalLayout_9.addWidget(self.label_11)

        self.groupBox_4 = QGroupBox(self.groupBox_2)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.groupBox_4.setFont(font)
        self.verticalLayout = QVBoxLayout(self.groupBox_4)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.histogram_radio = QRadioButton(self.groupBox_4)
        self.histogram_radio.setObjectName(u"histogram_radio")
        self.histogram_radio.setFont(font)
        self.histogram_radio.setChecked(True)

        self.verticalLayout.addWidget(self.histogram_radio)

        self.pixel_count_radio = QRadioButton(self.groupBox_4)
        self.pixel_count_radio.setObjectName(u"pixel_count_radio")
        self.pixel_count_radio.setFont(font)

        self.verticalLayout.addWidget(self.pixel_count_radio)

        self.contrast_radio = QRadioButton(self.groupBox_4)
        self.contrast_radio.setObjectName(u"contrast_radio")
        self.contrast_radio.setFont(font)

        self.verticalLayout.addWidget(self.contrast_radio)

        self.all_methods_radio = QRadioButton(self.groupBox_4)
        self.all_methods_radio.setObjectName(u"all_methods_radio")
        self.all_methods_radio.setFont(font)

        self.verticalLayout.addWidget(self.all_methods_radio)


        self.verticalLayout_9.addWidget(self.groupBox_4)

        self.analyze_button = QPushButton(self.groupBox_2)
        self.analyze_button.setObjectName(u"analyze_button")
        self.analyze_button.setMinimumSize(QSize(0, 40))
        self.analyze_button.setFont(font)

        self.verticalLayout_9.addWidget(self.analyze_button)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_9.addItem(self.verticalSpacer_2)


        self.horizontalLayout.addWidget(self.groupBox_2)

        self.groupBox_3 = QGroupBox(Widget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.groupBox_3.setMinimumSize(QSize(500, 0))
        self.groupBox_3.setFont(font)

        self.horizontalLayout.addWidget(self.groupBox_3)

        self.horizontalLayout.setStretch(0, 3)
        self.horizontalLayout.setStretch(1, 3)
        self.horizontalLayout.setStretch(2, 7)

        self.horizontalLayout_2.addLayout(self.horizontalLayout)


        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Laser Speckle Analyzer", None))
        self.groupBox.setTitle(QCoreApplication.translate("Widget", u"Menu", None))
        self.label.setText(QCoreApplication.translate("Widget", u"Current: []", None))
        self.label_2.setText(QCoreApplication.translate("Widget", u"ROI: []", None))
        self.label_15.setText(QCoreApplication.translate("Widget", u"Intensity Slider", None))
        self.load_button.setText(QCoreApplication.translate("Widget", u"Load Image", None))
        self.reset_roi_button.setText(QCoreApplication.translate("Widget", u"Reset ROI", None))
        self.label_3.setText(QCoreApplication.translate("Widget", u"Instructions:\n"
"1. Load an image\n"
"2. Draw ROI by clicking\n"
"   and dragging\n"
"3. Select analysis type\n"
"4. Click Analyze button", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Widget", u"Statistics", None))
        self.label_9.setText(QCoreApplication.translate("Widget", u"Mean Intensity: []", None))
        self.label_10.setText(QCoreApplication.translate("Widget", u"Saturated Pixels: []", None))
        self.label_11.setText(QCoreApplication.translate("Widget", u"Contrast Ratio: []", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("Widget", u"Analysis Method", None))
        self.histogram_radio.setText(QCoreApplication.translate("Widget", u"Histogram Analysis", None))
        self.pixel_count_radio.setText(QCoreApplication.translate("Widget", u"Pixel Count Analysis", None))
        self.contrast_radio.setText(QCoreApplication.translate("Widget", u"Speckle Contrast Analysis", None))
        self.all_methods_radio.setText(QCoreApplication.translate("Widget", u"All Methods", None))
        self.analyze_button.setText(QCoreApplication.translate("Widget", u"Analyze ROI", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("Widget", u"Image", None))
    # retranslateUi

