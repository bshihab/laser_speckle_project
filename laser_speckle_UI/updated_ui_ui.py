# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'updated_ui.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QRadioButton,
    QSizePolicy, QSlider, QTextEdit, QVBoxLayout,
    QWidget)


class Ui_LaserSpeckleUI(object):
    def setupUi(self, LaserSpeckleUI):
        if not LaserSpeckleUI.objectName():
            LaserSpeckleUI.setObjectName(u"LaserSpeckleUI")
        LaserSpeckleUI.resize(1200, 800)
        LaserSpeckleUI.setStyleSheet(u"QWidget {\n"
"    font-family: Arial;\n"
"    font-size: 10pt;\n"
"    background-color: #f5f5f7;\n"
"    color: #333333;\n"
"}\n"
"\n"
"QGroupBox {\n"
"    border: 1px solid #cccccc;\n"
"    border-radius: 8px;\n"
"    margin-top: 1ex;\n"
"    font-weight: bold;\n"
"    background-color: white;\n"
"    color: #333333;\n"
"}\n"
"\n"
"QGroupBox::title {\n"
"    subcontrol-origin: margin;\n"
"    subcontrol-position: top center;\n"
"    padding: 0 5px;\n"
"    font-size: 11pt;\n"
"    color: #333333;\n"
"}\n"
"\n"
"QPushButton {\n"
"    background-color: #0066cc;\n"
"    color: white;\n"
"    border-radius: 5px;\n"
"    padding: 8px;\n"
"    font-weight: bold;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #0080ff;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #004c99;\n"
"}\n"
"\n"
"QLineEdit {\n"
"    border: 1px solid #cccccc;\n"
"    border-radius: 4px;\n"
"    padding: 4px;\n"
"    background-color: white;\n"
"    color: #333333;\n"
"}\n"
"\n"
"QSlider::groove:horizontal {\n"
""
                        "    border: 1px solid #cccccc;\n"
"    height: 8px;\n"
"    background: #ffffff;\n"
"    margin: 2px 0;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: #0066cc;\n"
"    border: 1px solid #5c5c5c;\n"
"    width: 18px;\n"
"    margin: -2px 0;\n"
"    border-radius: 9px;\n"
"}\n"
"\n"
"QRadioButton {\n"
"    padding: 6px;\n"
"    color: #333333;\n"
"}\n"
"\n"
"QRadioButton:checked {\n"
"    font-weight: bold;\n"
"}\n"
"\n"
"QTextEdit {\n"
"    border: 1px solid #cccccc;\n"
"    border-radius: 4px;\n"
"    background-color: white;\n"
"    color: #333333;\n"
"}\n"
"\n"
"QLabel {\n"
"    color: #333333;\n"
"}\n"
"\n"
"QLabel#statsLabel, QLabel#recommendationLabel {\n"
"    font-weight: bold;\n"
"    padding: 8px;\n"
"    background-color: #e0f0ff;\n"
"    border-radius: 4px;\n"
"    color: #333333;\n"
"}\n"
"")
        self.horizontalLayout = QHBoxLayout(LaserSpeckleUI)
        self.horizontalLayout.setSpacing(12)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.leftColumn = QWidget(LaserSpeckleUI)
        self.leftColumn.setObjectName(u"leftColumn")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(4)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.leftColumn.sizePolicy().hasHeightForWidth())
        self.leftColumn.setSizePolicy(sizePolicy)
        self.leftColumnLayout = QVBoxLayout(self.leftColumn)
        self.leftColumnLayout.setObjectName(u"leftColumnLayout")
        self.settingsGroup = QGroupBox(self.leftColumn)
        self.settingsGroup.setObjectName(u"settingsGroup")
        self.settingsLayout = QGridLayout(self.settingsGroup)
        self.settingsLayout.setObjectName(u"settingsLayout")
        self.exposureLabel = QLabel(self.settingsGroup)
        self.exposureLabel.setObjectName(u"exposureLabel")

        self.settingsLayout.addWidget(self.exposureLabel, 0, 0, 1, 1)

        self.exposureInput = QLineEdit(self.settingsGroup)
        self.exposureInput.setObjectName(u"exposureInput")
        self.exposureInput.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.settingsLayout.addWidget(self.exposureInput, 0, 1, 1, 1)

        self.frequencyLabel = QLabel(self.settingsGroup)
        self.frequencyLabel.setObjectName(u"frequencyLabel")

        self.settingsLayout.addWidget(self.frequencyLabel, 1, 0, 1, 1)

        self.frequencyInput = QLineEdit(self.settingsGroup)
        self.frequencyInput.setObjectName(u"frequencyInput")
        self.frequencyInput.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.settingsLayout.addWidget(self.frequencyInput, 1, 1, 1, 1)


        self.leftColumnLayout.addWidget(self.settingsGroup)

        self.controlGroup = QGroupBox(self.leftColumn)
        self.controlGroup.setObjectName(u"controlGroup")
        self.controlLayout = QHBoxLayout(self.controlGroup)
        self.controlLayout.setObjectName(u"controlLayout")
        self.startButton = QPushButton(self.controlGroup)
        self.startButton.setObjectName(u"startButton")
        icon = QIcon()
        icon.addFile(u"icons/play.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.startButton.setIcon(icon)

        self.controlLayout.addWidget(self.startButton)

        self.stopButton = QPushButton(self.controlGroup)
        self.stopButton.setObjectName(u"stopButton")
        icon1 = QIcon()
        icon1.addFile(u"icons/stop.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.stopButton.setIcon(icon1)

        self.controlLayout.addWidget(self.stopButton)


        self.leftColumnLayout.addWidget(self.controlGroup)

        self.currentGroup = QGroupBox(self.leftColumn)
        self.currentGroup.setObjectName(u"currentGroup")
        self.currentLayout = QVBoxLayout(self.currentGroup)
        self.currentLayout.setObjectName(u"currentLayout")
        self.currentLabel = QLabel(self.currentGroup)
        self.currentLabel.setObjectName(u"currentLabel")
        self.currentLabel.setAlignment(Qt.AlignCenter)

        self.currentLayout.addWidget(self.currentLabel)

        self.currentSlider = QSlider(self.currentGroup)
        self.currentSlider.setObjectName(u"currentSlider")
        self.currentSlider.setMaximum(100)
        self.currentSlider.setValue(50)
        self.currentSlider.setOrientation(Qt.Horizontal)
        self.currentSlider.setTickPosition(QSlider.TicksBelow)
        self.currentSlider.setTickInterval(10)

        self.currentLayout.addWidget(self.currentSlider)


        self.leftColumnLayout.addWidget(self.currentGroup)

        self.previewGroup = QGroupBox(self.leftColumn)
        self.previewGroup.setObjectName(u"previewGroup")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.previewGroup.sizePolicy().hasHeightForWidth())
        self.previewGroup.setSizePolicy(sizePolicy1)
        self.previewLayout = QVBoxLayout(self.previewGroup)
        self.previewLayout.setObjectName(u"previewLayout")

        self.leftColumnLayout.addWidget(self.previewGroup)


        self.horizontalLayout.addWidget(self.leftColumn)

        self.middleColumn = QWidget(LaserSpeckleUI)
        self.middleColumn.setObjectName(u"middleColumn")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(3)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.middleColumn.sizePolicy().hasHeightForWidth())
        self.middleColumn.setSizePolicy(sizePolicy2)
        self.middleColumnLayout = QVBoxLayout(self.middleColumn)
        self.middleColumnLayout.setObjectName(u"middleColumnLayout")
        self.analysisGroup = QGroupBox(self.middleColumn)
        self.analysisGroup.setObjectName(u"analysisGroup")
        self.analysisLayout = QVBoxLayout(self.analysisGroup)
        self.analysisLayout.setObjectName(u"analysisLayout")
        self.histogramRadio = QRadioButton(self.analysisGroup)
        self.histogramRadio.setObjectName(u"histogramRadio")
        self.histogramRadio.setChecked(True)

        self.analysisLayout.addWidget(self.histogramRadio)

        self.pixelCountRadio = QRadioButton(self.analysisGroup)
        self.pixelCountRadio.setObjectName(u"pixelCountRadio")

        self.analysisLayout.addWidget(self.pixelCountRadio)

        self.contrastRadio = QRadioButton(self.analysisGroup)
        self.contrastRadio.setObjectName(u"contrastRadio")

        self.analysisLayout.addWidget(self.contrastRadio)

        self.allMethodsRadio = QRadioButton(self.analysisGroup)
        self.allMethodsRadio.setObjectName(u"allMethodsRadio")

        self.analysisLayout.addWidget(self.allMethodsRadio)

        self.analyzeButton = QPushButton(self.analysisGroup)
        self.analyzeButton.setObjectName(u"analyzeButton")

        self.analysisLayout.addWidget(self.analyzeButton)


        self.middleColumnLayout.addWidget(self.analysisGroup)

        self.statsGroup = QGroupBox(self.middleColumn)
        self.statsGroup.setObjectName(u"statsGroup")
        self.statsLayout = QVBoxLayout(self.statsGroup)
        self.statsLayout.setObjectName(u"statsLayout")
        self.meanLabel = QLabel(self.statsGroup)
        self.meanLabel.setObjectName(u"meanLabel")

        self.statsLayout.addWidget(self.meanLabel)

        self.saturationLabel = QLabel(self.statsGroup)
        self.saturationLabel.setObjectName(u"saturationLabel")

        self.statsLayout.addWidget(self.saturationLabel)

        self.contrastLabel = QLabel(self.statsGroup)
        self.contrastLabel.setObjectName(u"contrastLabel")

        self.statsLayout.addWidget(self.contrastLabel)

        self.recommendationLabel = QLabel(self.statsGroup)
        self.recommendationLabel.setObjectName(u"recommendationLabel")
        self.recommendationLabel.setAlignment(Qt.AlignCenter)
        self.recommendationLabel.setWordWrap(True)

        self.statsLayout.addWidget(self.recommendationLabel)


        self.middleColumnLayout.addWidget(self.statsGroup)

        self.logGroup = QGroupBox(self.middleColumn)
        self.logGroup.setObjectName(u"logGroup")
        sizePolicy1.setHeightForWidth(self.logGroup.sizePolicy().hasHeightForWidth())
        self.logGroup.setSizePolicy(sizePolicy1)
        self.logLayout = QVBoxLayout(self.logGroup)
        self.logLayout.setObjectName(u"logLayout")
        self.logText = QTextEdit(self.logGroup)
        self.logText.setObjectName(u"logText")
        self.logText.setReadOnly(True)

        self.logLayout.addWidget(self.logText)


        self.middleColumnLayout.addWidget(self.logGroup)


        self.horizontalLayout.addWidget(self.middleColumn)

        self.rightColumn = QWidget(LaserSpeckleUI)
        self.rightColumn.setObjectName(u"rightColumn")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(5)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.rightColumn.sizePolicy().hasHeightForWidth())
        self.rightColumn.setSizePolicy(sizePolicy3)
        self.rightColumnLayout = QVBoxLayout(self.rightColumn)
        self.rightColumnLayout.setObjectName(u"rightColumnLayout")
        self.rawImageGroup = QGroupBox(self.rightColumn)
        self.rawImageGroup.setObjectName(u"rawImageGroup")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(1)
        sizePolicy4.setHeightForWidth(self.rawImageGroup.sizePolicy().hasHeightForWidth())
        self.rawImageGroup.setSizePolicy(sizePolicy4)
        self.rawImageLayout = QVBoxLayout(self.rawImageGroup)
        self.rawImageLayout.setObjectName(u"rawImageLayout")

        self.rightColumnLayout.addWidget(self.rawImageGroup)

        self.speckleImageGroup = QGroupBox(self.rightColumn)
        self.speckleImageGroup.setObjectName(u"speckleImageGroup")
        sizePolicy4.setHeightForWidth(self.speckleImageGroup.sizePolicy().hasHeightForWidth())
        self.speckleImageGroup.setSizePolicy(sizePolicy4)
        self.speckleImageLayout = QVBoxLayout(self.speckleImageGroup)
        self.speckleImageLayout.setObjectName(u"speckleImageLayout")

        self.rightColumnLayout.addWidget(self.speckleImageGroup)

        self.fileControlLayout = QHBoxLayout()
        self.fileControlLayout.setObjectName(u"fileControlLayout")
        self.loadButton = QPushButton(self.rightColumn)
        self.loadButton.setObjectName(u"loadButton")

        self.fileControlLayout.addWidget(self.loadButton)

        self.saveButton = QPushButton(self.rightColumn)
        self.saveButton.setObjectName(u"saveButton")

        self.fileControlLayout.addWidget(self.saveButton)

        self.resetButton = QPushButton(self.rightColumn)
        self.resetButton.setObjectName(u"resetButton")

        self.fileControlLayout.addWidget(self.resetButton)


        self.rightColumnLayout.addLayout(self.fileControlLayout)


        self.horizontalLayout.addWidget(self.rightColumn)


        self.retranslateUi(LaserSpeckleUI)

        QMetaObject.connectSlotsByName(LaserSpeckleUI)
    # setupUi

    def retranslateUi(self, LaserSpeckleUI):
        LaserSpeckleUI.setWindowTitle(QCoreApplication.translate("LaserSpeckleUI", u"Laser Speckle Analyzer - Modern UI", None))
        self.settingsGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Capture Settings", None))
        self.exposureLabel.setText(QCoreApplication.translate("LaserSpeckleUI", u"Exposure Time (ms):", None))
        self.exposureInput.setText(QCoreApplication.translate("LaserSpeckleUI", u"50", None))
        self.frequencyLabel.setText(QCoreApplication.translate("LaserSpeckleUI", u"Update Frequency (ms):", None))
        self.frequencyInput.setText(QCoreApplication.translate("LaserSpeckleUI", u"500", None))
        self.controlGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Capture Control", None))
        self.startButton.setText(QCoreApplication.translate("LaserSpeckleUI", u"Start Capture", None))
        self.stopButton.setText(QCoreApplication.translate("LaserSpeckleUI", u"Stop Capture", None))
        self.currentGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Laser Current Control", None))
        self.currentLabel.setText(QCoreApplication.translate("LaserSpeckleUI", u"Current: 50%", None))
        self.previewGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Preview with ROI", None))
        self.analysisGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Analysis Method", None))
        self.histogramRadio.setText(QCoreApplication.translate("LaserSpeckleUI", u"Histogram Analysis", None))
        self.pixelCountRadio.setText(QCoreApplication.translate("LaserSpeckleUI", u"Pixel Count Analysis", None))
        self.contrastRadio.setText(QCoreApplication.translate("LaserSpeckleUI", u"Contrast Analysis", None))
        self.allMethodsRadio.setText(QCoreApplication.translate("LaserSpeckleUI", u"All Methods", None))
        self.analyzeButton.setText(QCoreApplication.translate("LaserSpeckleUI", u"Analyze ROI", None))
        self.statsGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Statistics", None))
        self.meanLabel.setText(QCoreApplication.translate("LaserSpeckleUI", u"Mean Intensity: --", None))
        self.saturationLabel.setText(QCoreApplication.translate("LaserSpeckleUI", u"Saturated Pixels: --", None))
        self.contrastLabel.setText(QCoreApplication.translate("LaserSpeckleUI", u"Contrast Ratio: --", None))
        self.recommendationLabel.setText(QCoreApplication.translate("LaserSpeckleUI", u"Analyze an image for recommendations", None))
        self.logGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Activity Log", None))
        self.logText.setHtml(QCoreApplication.translate("LaserSpeckleUI", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Arial'; font-size:10pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Starting Laser Speckle Analyzer...</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Ready for capture.</p></body></html>", None))
        self.rawImageGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Raw Image", None))
        self.speckleImageGroup.setTitle(QCoreApplication.translate("LaserSpeckleUI", u"Speckle Analysis", None))
        self.loadButton.setText(QCoreApplication.translate("LaserSpeckleUI", u"Load Image", None))
        self.saveButton.setText(QCoreApplication.translate("LaserSpeckleUI", u"Save Results", None))
        self.resetButton.setText(QCoreApplication.translate("LaserSpeckleUI", u"Reset ROI", None))
    # retranslateUi

