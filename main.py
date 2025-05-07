import sqlite3
import requests
import datetime
import random
import math
import tkinter as tk
from tkinter import messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def create_database():
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        date TEXT,
        open_price REAL,
        close_price REAL,
        volume REAL
    )
    """)
    conn.commit()
    conn.close()

def fetch_stock_data(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5mo"
    headers = {"User-Agent": "Mozilla/5.0"}
    try: 
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "chart" in data and "result" in data["chart"]:
            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {}).get("quote", [{}])[0]
            conn = sqlite3.connect("portfolio.db")
            cursor = conn.cursor()
            for i in range(len(timestamps)):
                date = datetime.datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d')
                open_price = indicators.get("open", [None])[i]
                close_price = indicators.get("close", [None])[i]
                volume = indicators.get("volume", [None])[i]
                if open_price is not None and close_price is not None and volume is not None:
                    cursor.execute("""
                    INSERT INTO stocks (symbol, date, open_price, close_price, volume)
                    VALUES (?, ?, ?, ?, ?)
                    """, (symbol, date, open_price, close_price, volume))
            conn.commit()
            conn.close()
            print(f"Stock data for {symbol} stored in database.")
        else:
            print("Invalid data format received from Yahoo Finance.")
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")

def get_daily_returns(symbol):
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    cursor.execute("SELECT date, close_price FROM stocks WHERE symbol = ? ORDER BY date", (symbol,))
    rows = cursor.fetchall()
    conn.close()
    if len(rows) < 2:
        print("Not enough data for simulation.")
        return None
    returns = [(rows[i][1] - rows[i-1][1]) / rows[i-1][1] for i in range(1, len(rows))]
    return returns

def monte_carlo_simulation(symbol, days=30, simulations=1000):
    returns = get_daily_returns(symbol)
    if not returns:
        return None
    avg_return = sum(returns) / len(returns)
    volatility = (max(returns) - min(returns)) / 2
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    cursor.execute("SELECT close_price FROM stocks WHERE symbol = ? ORDER BY date DESC LIMIT 1", (symbol,))
    last_close_price = cursor.fetchone()[0]
    conn.close()
    simulations_result = []
    for _ in range(simulations):
        price = last_close_price
        path = [price]
        for _ in range(days):
            random_factor = random.gauss(avg_return, volatility)
            price *= (1 + random_factor)
            path.append(price)
        simulations_result.append(path)
    return simulations_result

def compute_risk_metrics(final_prices, risk_free_rate=0.01):
    sorted_prices = sorted(final_prices)
    index_5 = int(0.05 * len(sorted_prices))
    var_95 = sorted_prices[index_5]
    expected_return = sum(final_prices) / len(final_prices)
    volatility = math.sqrt(sum((x - expected_return) ** 2 for x in final_prices) / len(final_prices))
    sharpe_ratio = (expected_return - risk_free_rate) / volatility if volatility != 0 else 0
    return var_95, expected_return, sharpe_ratio

#########################################
# Single Page Tkinter GUI Application   #
#########################################

class FinancialOptimizerApp(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Financial Optimizer")
        self.geometry("800x600")
        
        # Top navigation frame
        nav_frame = tk.Frame(self)
        nav_frame.pack(side="top", fill="x")
        tk.Button(nav_frame, text="Investment Simulation", command=self.show_simulation_frame).pack(side="left", padx=5, pady=5)
        tk.Button(nav_frame, text="Risk Analysis", command=self.show_risk_frame).pack(side="left", padx=5, pady=5)
        tk.Button(nav_frame, text="Portfolio Return", command=self.show_portfolio_frame).pack(side="left", padx=5, pady=5)
        
        # Container frame for pages
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        
        # Initialize frames dictionary
        self.frames = {}
        for F in (SimulationFrame, RiskFrame, PortfolioFrame):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_simulation_frame()  # default page

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
    
    def show_simulation_frame(self):
        self.show_frame(SimulationFrame)
    
    def show_risk_frame(self):
        self.show_frame(RiskFrame)
    
    def show_portfolio_frame(self):
        self.show_frame(PortfolioFrame)

class SimulationFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        tk.Label(self, text="Investment Simulation", font=("Arial", 16)).pack(pady=10)
        
        form_frame = tk.Frame(self)
        form_frame.pack(pady=10)
        
        tk.Label(form_frame, text="Stock Symbol:").grid(row=0, column=0, sticky="e")
        self.symbol_entry = tk.Entry(form_frame)
        self.symbol_entry.grid(row=0, column=1)
        
        tk.Label(form_frame, text="Days:").grid(row=1, column=0, sticky="e")
        self.days_entry = tk.Entry(form_frame)
        self.days_entry.grid(row=1, column=1)
        
        tk.Label(form_frame, text="Simulations:").grid(row=2, column=0, sticky="e")
        self.sim_entry = tk.Entry(form_frame)
        self.sim_entry.grid(row=2, column=1)
        
        tk.Button(self, text="Run Simulation", command=self.run_simulation).pack(pady=10)
        
        # Canvas for plot
        self.plot_canvas = None

    def run_simulation(self):
        symbol = self.symbol_entry.get().strip().upper() or "AAPL"
        try:
            days = int(self.days_entry.get())
        except:
            days = 30
        try:
            simulations = int(self.sim_entry.get())
        except:
            simulations = 1000
        sim_paths = monte_carlo_simulation(symbol, days, simulations)
        if not sim_paths:
            messagebox.showerror("Error", "No simulation data available. Check stock data.")
            return
        
        # Create plot using matplotlib
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        for path in sim_paths:
            ax.plot(path, linewidth=0.8, alpha=0.5)
        ax.set_title(f"Monte Carlo Simulation for {symbol}")
        ax.set_xlabel("Days")
        ax.set_ylabel("Price")
        
        if self.plot_canvas:
            self.plot_canvas.get_tk_widget().destroy()
        self.plot_canvas = FigureCanvasTkAgg(fig, master=self)
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(pady=10)

class RiskFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        tk.Label(self, text="Risk Analysis", font=("Arial", 16)).pack(pady=10)
        
        form_frame = tk.Frame(self)
        form_frame.pack(pady=10)
        
        tk.Label(form_frame, text="Stock Symbol:").grid(row=0, column=0, sticky="e")
        self.symbol_entry = tk.Entry(form_frame)
        self.symbol_entry.grid(row=0, column=1)
        
        tk.Label(form_frame, text="Days:").grid(row=1, column=0, sticky="e")
        self.days_entry = tk.Entry(form_frame)
        self.days_entry.grid(row=1, column=1)
        
        tk.Label(form_frame, text="Simulations:").grid(row=2, column=0, sticky="e")
        self.sim_entry = tk.Entry(form_frame)
        self.sim_entry.grid(row=2, column=1)
        
        tk.Button(self, text="Run Risk Analysis", command=self.run_risk).pack(pady=10)
        
        self.metrics_label = tk.Label(self, font=("Arial", 12))
        self.metrics_label.pack(pady=5)
        
        self.plot_canvas = None

    def run_risk(self):
        symbol = self.symbol_entry.get().strip().upper() or "AAPL"
        try:
            days = int(self.days_entry.get())
        except:
            days = 30
        try:
            simulations = int(self.sim_entry.get())
        except:
            simulations = 1000
        sim_paths = monte_carlo_simulation(symbol, days, simulations)
        if not sim_paths:
            messagebox.showerror("Error", "No simulation data available. Check stock data.")
            return
        final_prices = [path[-1] for path in sim_paths]
        var_95, expected_return, sharpe_ratio = compute_risk_metrics(final_prices)
        metrics = (f"Expected Return: {expected_return:.2f}\n"
                   f"VaR (95%): {var_95:.2f}\n"
                   f"Sharpe Ratio: {sharpe_ratio:.2f}")
        self.metrics_label.config(text=metrics)
        
        # Create plot using matplotlib
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        for path in sim_paths:
            ax.plot(path, linewidth=0.8, alpha=0.5)
        ax.set_title(f"Risk Analysis for {symbol}")
        ax.set_xlabel("Days")
        ax.set_ylabel("Price")
        
        if self.plot_canvas:
            self.plot_canvas.get_tk_widget().destroy()
        self.plot_canvas = FigureCanvasTkAgg(fig, master=self)
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().pack(pady=10)

class PortfolioFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        tk.Label(self, text="Portfolio Return Calculator", font=("Arial", 16)).pack(pady=10)
        tk.Label(self, text="Enter number of shares for each stock:", font=("Arial", 12)).pack(pady=5)
        
        self.stocks = ["AAPL", "GOOGL", "MSFT"]
        self.qty_entries = {}
        for sym in self.stocks:
            frame = tk.Frame(self)
            frame.pack(pady=2)
            tk.Label(frame, text=f"{sym}:").pack(side="left")
            entry = tk.Entry(frame, width=10)
            entry.pack(side="left")
            self.qty_entries[sym] = entry
        
        tk.Label(self, text="Days to simulate:", font=("Arial", 12)).pack(pady=5)
        self.days_entry = tk.Entry(self, width=10)
        self.days_entry.pack(pady=5)
        
        tk.Button(self, text="Calculate Portfolio Return", command=self.run_portfolio).pack(pady=10)
        
        self.results_label = tk.Label(self, font=("Arial", 12), justify="left")
        self.results_label.pack(pady=10)

    def run_portfolio(self):
        try:
            days = int(self.days_entry.get())
        except:
            days = 30
        total_initial = 0
        total_predicted = 0
        results_text = ""
        for sym in self.stocks:
            try:
                qty = float(self.qty_entries[sym].get())
            except:
                qty = 0
            conn = sqlite3.connect("portfolio.db")
            cursor = conn.cursor()
            cursor.execute("SELECT close_price FROM stocks WHERE symbol = ? ORDER BY date DESC LIMIT 1", (sym,))
            row = cursor.fetchone()
            conn.close()
            if row is None:
                continue
            initial_price = row[0]
            sim_paths = monte_carlo_simulation(sym, days, simulations=100)
            if not sim_paths:
                continue
            final_prices = [path[-1] for path in sim_paths]
            avg_final_price = sum(final_prices) / len(final_prices)
            total_initial += qty * initial_price
            total_predicted += qty * avg_final_price
            results_text += f"{sym}: Qty = {qty}, Initial Price = {initial_price:.2f}, Predicted Avg = {avg_final_price:.2f}\n"
        if total_initial == 0:
            messagebox.showerror("Error", "No valid data for portfolio calculation.")
            return
        overall_return = ((total_predicted - total_initial) / total_initial) * 100
        results_text += f"\nTotal Initial Value: {total_initial:.2f}\n"
        results_text += f"Predicted Portfolio Value: {total_predicted:.2f}\n"
        results_text += f"Overall Return: {overall_return:.2f}%"
        self.results_label.config(text=results_text)



if __name__ == "__main__":
    create_database()
    # Fetch sample data for these stocks if not already in DB.
    for sym in ["AAPL", "GOOGL", "MSFT"]:
        fetch_stock_data(sym)
    app = FinancialOptimizerApp()
    app.mainloop()