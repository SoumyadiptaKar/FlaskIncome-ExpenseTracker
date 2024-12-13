from application import db
from datetime import datetime

class IncomeExpenses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)

    def __repr__(self):
        return f"<IncomeExpenses {self.description} - {self.amount}>"

class MonthlyIncome(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    income = db.Column(db.Float, nullable=False)
    date_set = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MonthlyIncome {self.income}>'