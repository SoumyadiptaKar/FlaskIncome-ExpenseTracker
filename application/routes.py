from flask import render_template, redirect, url_for, request, jsonify
from application import app, db
import plotly.express as px
from application.models import IncomeExpenses, MonthlyIncome
from datetime import datetime
import pandas as pd
from sqlalchemy import extract

@app.route('/')
def index():
    expenses = IncomeExpenses.query.order_by(IncomeExpenses.date).all()
    return render_template('index.html', expenses=expenses)

@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        date_str = request.form['date']
        
        # Convert the date string to a datetime object
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        month = date_obj.month
        year = date_obj.year

        income_entry = MonthlyIncome.query.filter_by(date_set=datetime(year,month,1)).first()

        if not income_entry:
            return "You cannot add expences for this month without setting a monthly income first.", 400

        # Create the new expense record
        new_expense = IncomeExpenses(description=description, amount=amount, date=date_obj)
        db.session.add(new_expense)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('add_expense.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    expense = IncomeExpenses.query.get_or_404(id)
    
    if request.method == 'POST':
        expense.description = request.form['description']
        expense.amount = float(request.form['amount'])
        date_str = request.form['date']
        expense.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        db.session.commit()
        
        return redirect(url_for('index'))

    return render_template('edit_expense.html', expense=expense)

@app.route('/delete/<int:id>', methods=['GET', 'POST'])
def delete_expense(id):
    expense = IncomeExpenses.query.get_or_404(id)

    if request.method == 'POST':
        db.session.delete(expense)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('delete_expense.html', expense=expense)


@app.route('/dashboard')
def dashboard():
    # Get current month and year
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Filter expenses for the current month and year
    expenses = IncomeExpenses.query.filter(
        extract('year', IncomeExpenses.date) == current_year,
        extract('month', IncomeExpenses.date) == current_month
    ).order_by(IncomeExpenses.date).all()

    # Calculate the total spent in each description
    expense_data = {}
    for expense in expenses:
        description = expense.description
        amount = expense.amount
        if description not in expense_data:
            expense_data[description] = 0
        expense_data[description] += amount

    descriptions = list(expense_data.keys())
    amounts = list(expense_data.values())

    # Create Bar Chart for Expenses by Description
    fig_expenses = px.bar(
        x=descriptions, 
        y=amounts, 
        labels={'x': 'Description', 'y': 'Amount'},
        title="Expenses by Description"
    )

    # Time Series Line Chart (Expenses Over Time) for the current month
    expense_dates = [expense.date for expense in expenses]
    expense_amounts = [expense.amount for expense in expenses]

    fig_line = px.line(
        x=expense_dates,
        y=expense_amounts,
        title="Expenses Over Time",
        labels={'x': 'Date', 'y': 'Expense Amount'}
    )

    # Get monthly income for the current month
    monthly_income_record = MonthlyIncome.query.filter(
        extract('year', MonthlyIncome.date_set) == current_year,
        extract('month', MonthlyIncome.date_set) == current_month
    ).order_by(MonthlyIncome.date_set.desc()).first()
    
    if monthly_income_record:
        monthly_income = monthly_income_record.income
        total_expenses = sum(amounts)
        savings = monthly_income - total_expenses
    else:
        monthly_income = 0
        total_expenses = 0
        savings = 0

    # Create Pie Chart for Savings vs Utilized
    pie_data = {'Utilized': total_expenses, 'Saved': savings}
    fig_pie = px.pie(
        names=list(pie_data.keys()), 
        values=list(pie_data.values()),
        title="Savings vs Utilized"
    )

    # Convert the figures to HTML
    bar_chart_html = fig_expenses.to_html(full_html=False)
    pie_chart_html = fig_pie.to_html(full_html=False)
    line_graph_html = fig_line.to_html(full_html=False)

    # Render the dashboard with total expenditure and balance
    return render_template(
        'dashboard.html', 
        bar_chart_html=bar_chart_html,
        pie_chart_html=pie_chart_html,
        line_graph_html=line_graph_html,
        total_expenses=total_expenses,
        savings=savings,
        monthly_income=monthly_income
    )

@app.route('/monthly_dashboard', methods=['GET', 'POST'])
def monthly_dashboard():
    # Fetch all expenses and group them by month and year
    expenses = IncomeExpenses.query.order_by(IncomeExpenses.date).all()
    data = []
    for expense in expenses:
        year_month = expense.date.strftime("%Y-%m")  # Format: "YYYY-MM"
        data.append({
            'year_month': year_month,
            'description': expense.description,
            'amount': expense.amount,
            'date': expense.date
        })

    # Create a DataFrame for easier manipulation
    df_expenses = pd.DataFrame(data)

    # Calculate total expenses for each month
    monthly_expenses = df_expenses.groupby('year_month')['amount'].sum().reset_index()
    monthly_expenses = monthly_expenses.sort_values('year_month')

    # Create bar chart of monthly expenses
    fig_expenses = px.bar(
        monthly_expenses,
        x='year_month', 
        y='amount',
        labels={'year_month': 'Month', 'amount': 'Total Expenses'},
        title="Monthly Expenses"
    )

    # Get monthly income for each month
    monthly_income = MonthlyIncome.query.all()
    income_data = {income.date_set.strftime("%Y-%m"): income.income for income in monthly_income}

    # Create Pie Chart (Savings vs Utilized) for each month
    pie_charts_html = {}
    for month in monthly_expenses['year_month']:
        total_expense = monthly_expenses[monthly_expenses['year_month'] == month]['amount'].values[0]
        income = income_data.get(month, 0)
        savings = income - total_expense if income else 0

        # Pie chart data
        pie_data = {'Utilized': total_expense, 'Saved': savings}
        fig_pie = px.pie(names=list(pie_data.keys()), values=list(pie_data.values()), title=f"Savings vs Utilized for {month}")
        pie_charts_html[month] = fig_pie.to_html(full_html=False)

    # Line graph for expenses over time
    expense_dates = [expense.date for expense in expenses]
    expense_amounts = [expense.amount for expense in expenses]

    fig_line = px.line(
        x=expense_dates,
        y=expense_amounts,
        title="Expenses Over Time",
        labels={'x': 'Date', 'y': 'Expense Amount'}
    )

    # Handle the POST request when a month is selected
    if request.method == 'POST':
        selected_month = request.form['month']
        selected_year = request.form['year']
        selected_year_month = f"{selected_year}-{selected_month}"

        # Filter expenses for the selected month
        filtered_expenses = df_expenses[df_expenses['year_month'] == selected_year_month]
        expense_data = {}
        for expense in filtered_expenses.itertuples():
            description = expense.description
            amount = expense.amount
            if description not in expense_data:
                expense_data[description] = 0
            expense_data[description] += amount

        descriptions = list(expense_data.keys())
        amounts = list(expense_data.values())

        # Create Bar Chart for selected month
        fig_expenses_selected = px.bar(
            x=descriptions,
            y=amounts,
            labels={'x': 'Description', 'y': 'Amount'},
            title=f"Expenses for {selected_year_month} by Description"
        )

        # Get pie chart for the selected month
        total_expense = monthly_expenses[monthly_expenses['year_month'] == selected_year_month]['amount'].values[0]
        income = income_data.get(selected_year_month, 0)
        savings = income - total_expense if income else 0

        pie_data = {'Utilized': total_expense, 'Saved': savings}
        fig_pie_selected = px.pie(names=list(pie_data.keys()), values=list(pie_data.values()), title=f"Savings vs Utilized for {selected_year_month}")

        # Convert selected month graphs to HTML
        selected_bar_chart_html = fig_expenses_selected.to_html(full_html=False)
        selected_pie_chart_html = fig_pie_selected.to_html(full_html=False)

        return jsonify({
            'bar_chart_html': selected_bar_chart_html,
            'pie_chart_html': selected_pie_chart_html
        })

    # If it's a GET request, load the default data
    return render_template(
        'monthly_dashboard.html', 
        bar_chart_html=fig_expenses.to_html(full_html=False),
        pie_charts_html=pie_charts_html,
        line_graph_html=fig_line.to_html(full_html=False),
        monthly_expenses=monthly_expenses,
        income_data=income_data
    )

@app.route('/set_income', methods=['GET', 'POST'])
def set_income():
    if request.method == 'POST':
        income = request.form['income']
        month = request.form['month']
        year = datetime.now().year  
        
        date_set = datetime(year, int(month), 1)

        new_income = MonthlyIncome(income=income, date_set=date_set)
        db.session.add(new_income)
        db.session.commit()

        return redirect(url_for('monthly_dashboard'))
    
    return render_template('set_income.html')