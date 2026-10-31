import csv
import os
import math
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "expense-tracker-secret-key"

# Keep the CSV file in the project folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, "expenses.csv")

FIELDNAMES = ["date", "amount", "category", "description"]
CATEGORIES = ["Food", "Travel", "Shopping", "Other"]


# Load expenses from CSV
def load_expenses():
    expenses = []

    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    amount = float(row["amount"])

                    if not math.isfinite(amount):
                        continue

                    expense = {
                        "date": row.get("date") or "not available",
                        "amount": amount,
                        "category": row["category"].title(),
                        "description": row["description"]
                    }
                    expenses.append(expense)

                except (ValueError, KeyError, TypeError):
                    continue

    return expenses


# Save a new expense
def save_expense(expense):
    file_exists = os.path.exists(FILE_NAME)

    with open(FILE_NAME, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)

        if not file_exists or os.path.getsize(FILE_NAME) == 0:
            writer.writeheader()

        writer.writerow(expense)


# Rewrite CSV with updated expenses
def save_all_expenses(expenses):
    with open(FILE_NAME, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(expenses)


# Delete an expense
def delete_expense(index):
    expenses = load_expenses()

    if index < 0 or index >= len(expenses):
        return False

    del expenses[index]
    save_all_expenses(expenses)

    return True


# Update an existing expense
def update_expense(index, updated_expense):
    expenses = load_expenses()

    if index < 0 or index >= len(expenses):
        return False

    expenses[index] = updated_expense
    save_all_expenses(expenses)

    return True


# Validate expense form data
def validate_expense_form():
    expense_date = request.form.get("date", "").strip()
    amount_input = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip().title()
    description = request.form.get("description", "").strip()

    if not expense_date:
        flash("Please select an expense date.", "error")
        return None

    try:
        datetime.strptime(expense_date, "%Y-%m-%d")
    except ValueError:
        flash("Invalid date! Please select a valid date.", "error")
        return None

    try:
        amount = float(amount_input)

        if not math.isfinite(amount) or amount <= 0:
            raise ValueError

    except ValueError:
        flash("Amount must be a valid number greater than zero.", "error")
        return None

    if category not in CATEGORIES:
        flash("Please select a valid category.", "error")
        return None

    if not description:
        flash("Description cannot be empty.", "error")
        return None

    return {
        "date": expense_date,
        "amount": amount,
        "category": category,
        "description": description
    }
# Add expense
@app.route("/add", methods=["POST"])
def add_expense():
    expense = validate_expense_form()

    if expense is None:
        return redirect(url_for("index"))

    save_expense(expense)

    flash("Expense added successfully!", "success")
    return redirect(url_for("index"))



# Home page
@app.route("/")
def index():
    expenses = load_expenses()
    filter_date = request.args.get("filter_date", "").strip()

    if filter_date:
        try:
            datetime.strptime(filter_date, "%Y-%m-%d")
            expenses = [
                expense for expense in expenses
                if expense["date"] == filter_date
            ]
        except ValueError:
            filter_date = ""
    total = sum(expense["amount"] for expense in expenses)

    # Category-wise summary
    category_totals = {}

    for expense in expenses:
        category = expense["category"]
        category_totals[category] = (
            category_totals.get(category, 0) + expense["amount"]
        )

    # Monthly summary
    selected_month = request.args.get(
        "month", date.today().strftime("%Y-%m")
    )

    try:
        datetime.strptime(selected_month, "%Y-%m")
    except ValueError:
        selected_month = date.today().strftime("%Y-%m")

    monthly_total = sum(
        expense["amount"]
        for expense in expenses
        if expense["date"].startswith(selected_month)
    )

    # Data for category-wise pie chart
    chart_categories = list(category_totals.keys())
    chart_category_amounts = list(category_totals.values())

    # Data for monthly spending bar chart
    monthly_totals = {}

    for expense in expenses:
        expense_date = expense["date"]

        try:
            parsed_date = datetime.strptime(expense_date, "%Y-%m-%d")
            month_label = parsed_date.strftime("%b %Y")

            monthly_totals[month_label] = (
                monthly_totals.get(month_label, 0)
                + expense["amount"]
            )
        except ValueError:
            continue

    # Sort months chronologically
    sorted_months = sorted(
        monthly_totals.keys(),
        key=lambda month: datetime.strptime(month, "%b %Y")
    )

    chart_months = sorted_months
    chart_month_amounts = [
        monthly_totals[month] for month in sorted_months
    ]

    return render_template(
        "index.html",
        expenses=expenses,
        filter_date=filter_date,
        total=total,
        category_totals=category_totals,
        selected_month=selected_month,
        monthly_total=monthly_total,
        today=date.today().isoformat(),
        chart_categories=chart_categories,
        chart_category_amounts=chart_category_amounts,
        chart_months=chart_months,
        chart_month_amounts=chart_month_amounts
    )
# Edit expense page
@app.route("/edit/<int:index>")
def edit_expense_page(index):
    expenses = load_expenses()

    if index < 0 or index >= len(expenses):
        flash("Invalid expense selected.", "error")
        return redirect(url_for("index"))

    return render_template(
        "edit.html",
        expense=expenses[index],
        index=index,
        categories=CATEGORIES
    )



# Save edited expense
@app.route("/edit/<int:index>", methods=["POST"])
def edit_expense(index):
    updated_expense = validate_expense_form()

    if updated_expense is None:
        return redirect(url_for("edit_expense_page", index=index))

    if update_expense(index, updated_expense):
        flash("Expense updated successfully!", "success")
    else:
        flash("Invalid expense selected.", "error")

    return redirect(url_for("index"))


# Delete expense
@app.route("/delete/<int:index>", methods=["POST"])
def remove_expense(index):
    if delete_expense(index):
        flash("Expense deleted successfully!", "success")
    else:
        flash("Invalid expense selected.", "error")

    return redirect(url_for("index"))


# Start Flask application
if __name__ == "__main__":
    app.run(debug=True)
