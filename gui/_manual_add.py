# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '_manual_add.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Wizard(object):
    def setupUi(self, Wizard):
        Wizard.setObjectName("Wizard")
        Wizard.setWindowModality(QtCore.Qt.NonModal)
        Wizard.resize(526, 405)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Wizard.sizePolicy().hasHeightForWidth())
        Wizard.setSizePolicy(sizePolicy)
        Wizard.setWizardStyle(QtWidgets.QWizard.AeroStyle)
        Wizard.setTitleFormat(QtCore.Qt.PlainText)
        Wizard.setSubTitleFormat(QtCore.Qt.PlainText)
        self.intro = QtWidgets.QWizardPage()
        self.intro.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.intro.setTitle("")
        self.intro.setSubTitle("")
        self.intro.setObjectName("intro")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.intro)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(self.intro)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.manual_input = QtWidgets.QPlainTextEdit(self.intro)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.manual_input.sizePolicy().hasHeightForWidth())
        self.manual_input.setSizePolicy(sizePolicy)
        self.manual_input.setMinimumSize(QtCore.QSize(0, 0))
        self.manual_input.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.manual_input.setObjectName("manual_input")
        self.verticalLayout.addWidget(self.manual_input)
        Wizard.addPage(self.intro)
        self.process = QtWidgets.QWizardPage()
        self.process.setObjectName("process")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.process)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.label_6 = QtWidgets.QLabel(self.process)
        self.label_6.setObjectName("label_6")
        self.verticalLayout_4.addWidget(self.label_6)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem1)
        self.processing_page = QtWidgets.QLabel(self.process)
        self.processing_page.setObjectName("processing_page")
        self.verticalLayout_4.addWidget(self.processing_page)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem2)
        self.progressBar = QtWidgets.QProgressBar(self.process)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setTextVisible(True)
        self.progressBar.setInvertedAppearance(False)
        self.progressBar.setFormat("%p%")
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout_4.addWidget(self.progressBar)
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_4.addItem(spacerItem3)
        self.gridLayout_4.addLayout(self.verticalLayout_4, 0, 0, 1, 1)
        Wizard.addPage(self.process)
        self.concl = QtWidgets.QWizardPage()
        self.concl.setObjectName("concl")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.concl)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.concl_info = QtWidgets.QLabel(self.concl)
        self.concl_info.setObjectName("concl_info")
        self.gridLayout_7.addWidget(self.concl_info, 0, 0, 1, 1)
        Wizard.addPage(self.concl)

        self.retranslateUi(Wizard)
        QtCore.QMetaObject.connectSlotsByName(Wizard)

    def retranslateUi(self, Wizard):
        _translate = QtCore.QCoreApplication.translate
        Wizard.setWindowTitle(_translate("Wizard", "수동 추가"))
        self.label.setText(_translate("Wizard", "분석할 페이지를 한 줄에 하나씩 적어주세요"))
        self.label_6.setText(_translate("Wizard", "분석 중입니다. 잠시만 기다려주세요."))
        self.processing_page.setText(_translate("Wizard", "검색 중인 사이트:"))
        self.concl_info.setText(_translate("Wizard", "분석을 종료합니다."))

