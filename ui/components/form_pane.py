from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QGridLayout
)
from PySide6.QtWidgets import QDateEdit
from PySide6.QtCore import QDate
import datetime
from loguru import logger
from case.sql_manage import CaseManager,VedisManager
class FormPanel(QWidget):
    def __init__(self,llm):
        super().__init__()
        self.llm = llm  
        self.setup_ui()
        self.initial_case_snapshot = self.capture_case_snapshot()
       
    def setup_ui(self):
        self.form_layout = QGridLayout()

        # 第1行
        self.form_layout.addWidget(QLabel("日期"), 0, 0)

        # 日期选择器
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.form_layout.addWidget(self.date_edit, 0, 1)

        # 病例下拉框
        self.form_layout.addWidget(QLabel("🔍"), 0, 2)
        self.case_selector = QComboBox()
        self.form_layout.addWidget(self.case_selector, 0, 3)
        # ------------------------------------------------------------
        self.form_layout.addWidget(QLabel("病例号"), 1, 0)
        self.case_id = QLineEdit()
        self.case_id.setReadOnly(True)
        self.case_id.setPlaceholderText("+ 生成")
        self.form_layout.addWidget(self.case_id, 1, 1)
        # ➕ 按钮
        self.new_case = QPushButton("➕新增")
        self.form_layout.addWidget(self.new_case, 1, 2)
        # 删除按钮
        self.del_case = QPushButton("🗑️删除")
        self.form_layout.addWidget(self.del_case, 1, 3)
        # ------------------------------------------------------------
        # 第2行
        self.form_layout.addWidget(QLabel("姓名"), 2, 0)
        self.name_input = QLineEdit()
        self.form_layout.addWidget(self.name_input, 2, 1)

        self.form_layout.addWidget(QLabel("手机号"), 2, 2)
        self.phone_input = QLineEdit()
        self.form_layout.addWidget(self.phone_input, 2, 3)

        # 第3行
        self.form_layout.addWidget(QLabel("宠物名"), 3, 0)
        self.pet_name_input = QLineEdit()
        self.form_layout.addWidget(self.pet_name_input, 3, 1)

        self.form_layout.addWidget(QLabel("物种"), 3, 2)
        self.species_select = QComboBox()
        self.species_select.addItems(["猫", "狗", "其他"])
        self.species_select.setCurrentIndex(-1) 
        self.form_layout.addWidget(self.species_select, 3, 3)

        # 第4行
        self.form_layout.addWidget(QLabel("品种"), 4, 0)
        self.breed_select =QComboBox()
        self.breed_select.addItems(["柯基", "斗牛", "其他"])
        self.breed_select.setCurrentIndex(-1) 
        self.form_layout.addWidget(self.breed_select, 4, 1)

        self.form_layout.addWidget(QLabel("体重"), 4, 2)
        self.weight_input = QLineEdit()
        self.form_layout.addWidget(self.weight_input, 4, 3)

        # 第5行
        self.form_layout.addWidget(QLabel("驱虫"), 5, 0)
        self.deworming_select = QComboBox()
        self.deworming_select.addItems(["是", "否"])
        self.deworming_select.setCurrentIndex(-1) 
        self.form_layout.addWidget(self.deworming_select, 5, 1)
        self.form_layout.addWidget(QLabel("绝育"), 5, 2)
        self.sterilization_select = QComboBox()
        self.sterilization_select.addItems(["是", "否"])
        self.sterilization_select.setCurrentIndex(-1) 
        self.form_layout.addWidget(self.sterilization_select, 5, 3)

        # 第6行 主诉
        self.form_layout.addWidget(QLabel("主诉"), 6, 0)
        self.complaint_text = QTextEdit()
        self.form_layout.addWidget(self.complaint_text, 6, 1, 4, 3)
        
        # 第7行 检查
        self.form_layout.addWidget(QLabel("检查"), 10, 0)
        self.checkup_text = QTextEdit()
        self.form_layout.addWidget(self.checkup_text, 10, 1, 2, 3)
        # 第8行 结果
        self.form_layout.addWidget(QLabel("检查结果"), 12, 0)
        self.results_text = QTextEdit()
        self.form_layout.addWidget(self.results_text, 12, 1, 2, 3)
        
        # 第7行 诊断
        self.form_layout.addWidget(QLabel("诊断："), 14, 0)
        self.diagnosis_text = QLineEdit()
        self.form_layout.addWidget(self.diagnosis_text, 14, 1, 1, 3)
        
        # 第6行 治疗
        self.form_layout.addWidget(QLabel("治疗"), 15, 0)
        self.treatment_text = QTextEdit()
        self.form_layout.addWidget(self.treatment_text, 15, 1, 2, 3)

        self.setLayout(self.form_layout)
        
        self.del_case.clicked.connect(self.delete)
            
    def clear(self):
        self.case_id.clear()
        self.name_input.clear()
        self.phone_input.clear()
        self.pet_name_input.clear()
        self.species_select.setCurrentIndex(-1)
        self.breed_select.setCurrentIndex(-1)
        self.weight_input.clear()
        self.deworming_select.setCurrentIndex(-1)
        self.sterilization_select.setCurrentIndex(-1)
        self.complaint_text.clear()
        self.diagnosis_text.clear()
        self.update_case_snapshot()
    def capture_case_snapshot(self):
                return {
                "name": self.name_input.text(),
                "phone": self.phone_input.text(),
                "pet_name": self.pet_name_input.text(),
                "species": self.species_select.currentText(),
                "breed": self.breed_select.currentText(),
                "weight": self.weight_input.text(),
                "deworming": self.deworming_select.currentText(),
                "sterilization": self.sterilization_select.currentText(),
                "complaint": self.complaint_text.toPlainText(),
                "checkup": self.checkup_text.toPlainText(),
                "results": self.checkup_text.toPlainText(),
                "diagnosis": self.diagnosis_text.text(),
                "treatment": self.treatment_text.toPlainText(),
                "dialogue": str(self.llm),
            }
    def update_case_snapshot(self):
        self.initial_case_snapshot = self.capture_case_snapshot()
    def is_case_modified(self):
        current = self.capture_case_snapshot()
        return current != self.initial_case_snapshot
    def is_case_empty(self):
        snapshot = self.capture_case_snapshot()
        is_empty = all(
    not value.strip() 
    for key, value in snapshot.items() 
    if key not in ["dialogue","species","breed","deworming","sterilization"]
)
        
        logger.info(f"当前病例是否为空: {is_empty}")
        logger.info(str([not value.strip() for key, value in snapshot.items() if key not in ["dialogue","species","breed","deworming","sterilization"]]))
        return is_empty
    def load(self, index):
        # if index < 0:
        #     return
        self.clear()  # 清空当前输入
        self.llm.clear()
        case_id = self.case_selector.itemText(index)
        record = CaseManager.get_one("case_id = ?", (case_id,))
        if not record:
            return
        self.case_id.setText(record["case_id"])
        self.name_input.setText(record["name"])
        self.phone_input.setText(record["phone"])
        self.pet_name_input.setText(record["pet_name"])
        self.species_select.setCurrentText(record["species"])
        self.breed_select.setCurrentText(record["breed"])
        self.weight_input.setText(record["weight"])
        self.deworming_select.setCurrentText(record["deworming"])
        self.sterilization_select.setCurrentText(record["sterilization"])
        self.complaint_text.setPlainText(record["complaint"])
        self.checkup_text.setPlainText(record["checkup"])
        self.results_text.setPlainText(record["results"])
        self.diagnosis_text.setText(record["diagnosis"])
        self.treatment_text.setPlainText(record["treatment"])
        dialogue = record["dialogue"]
        VedisManager.set("current_case_id", self.case_id.text())
        return dialogue
        
    def save(self):
        case_data = {
            "case_id": self.case_id.text(),
            "name": self.name_input.text(),
            "phone": self.phone_input.text(),
            "pet_name": self.pet_name_input.text(),
            "species": self.species_select.currentText(),
            "breed": self.breed_select.currentText(),
            "weight": self.weight_input.text(),
            "deworming": self.deworming_select.currentText(),
            "sterilization": self.sterilization_select.currentText(),
            "complaint": self.complaint_text.toPlainText(),
            "checkup": self.checkup_text.toPlainText(),
            "results": self.checkup_text.toPlainText(),
            "diagnosis": self.diagnosis_text.text(),
            "treatment": self.treatment_text.toPlainText(),
            "dialogue": str(self.llm)  
        }
        CaseManager.insert(case_data)
        self.initial_case_snapshot=self.capture_case_snapshot()
    def delete(self):
        CaseManager.delete("case_id = ?", (self.case_id.text(),))
        VedisManager.delete("current_case_id")
        self.clear()
        self.case_selector.removeItem(self.case_selector.currentIndex())
        self.llm.clear()  # 清空 LLM 对话内容
    def new(self):
        if  self.case_id.text().strip() and not self.is_case_empty():
            self.save()
            self.case_selector.addItem(self.case_id.text().strip())
            self.clear()
            self.llm.clear()
        # if not self.case_id.text().strip():
        #    #case_id 为空，说明是第一次创建 
        #     current_date = datetime.datetime.now().strftime("%Y%m%d")
        #     count = len(CaseManager.get_case_by_date())
        #     self.case_id.setText(f"{current_date}_{count+1}")
        #     VedisManager.set("current_case_id", self.case_id.text())
           
        # else:
        #     # case_id 不为空，说明是已有病例，检查是否修改
        #     if not self.is_case_empty() :
        #         self.save()
        #         self.case_selector.addItem(self.case_id.text().strip())
        #         self.clear()
        #         self.llm.clear()
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        count = len(CaseManager.get_case_by_date())
        self.case_id.setText(f"{current_date}_{count+1}")
        VedisManager.set("current_case_id", self.case_id.text())
            
            
            
 
