import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mlxtend.frequent_patterns import apriori, association_rules
from datetime import timedelta
from statsmodels.tsa.arima.model import ARIMA

# ===========================
# LOAD DATA (Upload CSV or Use Sample)
# ===========================
st.sidebar.subheader("📂 Upload Data")
uploaded_file = st.sidebar.file_uploader("/content/cleaned_ecommerce.csv", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    # Try to parse Date column if present
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
else:
    st.sidebar.info("Using sample dataset (upload to replace).")
    data = """OrderID,Date,CustomerID,Amount,Category
1,2023-01-01,C001,200,Electronics
2,2023-01-02,C002,150,Fashion
3,2023-01-03,C003,300,Home
4,2023-01-04,C002,250,Electronics
5,2023-01-05,C001,100,Fashion
6,2023-01-06,C004,400,Electronics
7,2023-01-07,C003,200,Fashion
8,2023-01-08,C001,350,Home
9,2023-01-09,C002,220,Electronics"""
    from io import StringIO
    df = pd.read_csv(StringIO(data))
    df["Date"] = pd.to_datetime(df["Date"])

# ===========================
# STREAMLIT APP
# ===========================
st.title("📊 E-commerce Sales Analytics Dashboard")

page = st.sidebar.radio("Go to:",
                        ["📂 Data Overview",
                         "👥 RFM Segmentation",
                         "🛒 Market Basket Analysis",
                         "📈 Sales Forecasting"])

# ----------------------------
# PAGE 1: Data Overview
# ----------------------------
if page == "📂 Data Overview":
    st.subheader("📂 Raw Data")
    st.write(df.head())

    # KPIs
    st.subheader("📌 KPIs")
    col1, col2 = st.columns(2)
    col1.metric("Total Sales", f"${df['Amount'].sum():,.0f}")
    col2.metric("Unique Customers", df["CustomerID"].nunique())

    # Sales Trend
    if "Date" in df.columns:
        st.subheader("📈 Daily Sales Trend")
        daily_sales = df.groupby("Date")["Amount"].sum()
        st.line_chart(daily_sales)

    # Sales by Category
    if "Category" in df.columns:
        st.subheader("🛍 Sales by Category")
        category_sales = df.groupby("Category")["Amount"].sum()
        st.bar_chart(category_sales)

# ----------------------------
# PAGE 2: RFM Segmentation
# ----------------------------
elif page == "👥 RFM Segmentation":
    if "Date" in df.columns:
        st.subheader("👥 Customer Segmentation (RFM)")
        snapshot_date = df["Date"].max() + timedelta(days=1)
        rfm = df.groupby("CustomerID").agg({
            "Date": lambda x: (snapshot_date - x.max()).days,
            "OrderID": "count",
            "Amount": "sum"
        }).rename(columns={"Date":"Recency","OrderID":"Frequency","Amount":"Monetary"})
        st.write(rfm)
    else:
        st.warning("Your dataset needs a 'Date' column for RFM.")

# ----------------------------
# PAGE 3: Market Basket Analysis
# ----------------------------
elif page == "🛒 Market Basket Analysis":
    if "Category" in df.columns and "OrderID" in df.columns:
        st.subheader("🛒 Market Basket Analysis")

        # User controls
        min_support = st.slider("Minimum Support", 0.01, 0.5, 0.05, 0.01)
        min_threshold = st.slider("Minimum Lift Threshold", 0.1, 5.0, 1.0, 0.1)

        # Create Basket Matrix
        basket = df.groupby(["OrderID", "Category"])["Amount"].sum().unstack().fillna(0)
        basket = basket.applymap(lambda x: 1 if x > 0 else 0)

        # Run Apriori with user-defined support
        frequent_items = apriori(basket, min_support=min_support, use_colnames=True)

        if frequent_items.empty:
            st.warning("⚠ No frequent itemsets found. Try lowering Minimum Support.")
        else:
            st.write("📌 Frequent Itemsets:")
            st.dataframe(frequent_items)

            # Show top frequent itemsets
            st.bar_chart(frequent_items.set_index("itemsets")["support"].nlargest(10))

            # Association rules
            rules = association_rules(frequent_items, metric="lift", min_threshold=min_threshold)

            if rules.empty:
                st.warning("⚠ No association rules found. Try lowering the Lift Threshold.")
            else:
                st.write("📌 Association Rules:")
                st.dataframe(rules[["antecedents", "consequents", "support", "confidence", "lift"]])

                # Network Graph of Rules
                import networkx as nx
                import matplotlib.pyplot as plt

                G = nx.DiGraph()

                for _, row in rules.iterrows():
                    for antecedent in row["antecedents"]:
                        for consequent in row["consequents"]:
                            G.add_edge(antecedent, consequent, weight=row["lift"])

                plt.figure(figsize=(8, 6))
                pos = nx.spring_layout(G, k=0.5)
                nx.draw(G, pos, with_labels=True, node_size=2000, node_color="lightblue", font_size=10, font_weight="bold")
                st.pyplot(plt.gcf())
    else:
        st.warning("⚠ Your dataset needs both 'OrderID' and 'Category' columns for Market Basket Analysis.")

# ----------------------------
# PAGE 4: Sales Forecasting
# ----------------------------
elif page == "📈 Sales Forecasting":
    if "Date" in df.columns:
        st.subheader("📈 Sales Forecasting with ARIMA")

        ts = df.groupby("Date")["Amount"].sum()

        try:
            model = ARIMA(ts, order=(1,1,1))
            model_fit = model.fit()
            forecast_steps = 7
            forecast = model_fit.forecast(steps=forecast_steps)

            # Plot
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ts.plot(ax=ax, label="Historical Sales")
            forecast_index = pd.date_range(ts.index[-1] + timedelta(days=1),
                                           periods=forecast_steps, freq="D")
            forecast_series = pd.Series(forecast, index=forecast_index)
            forecast_series.plot(ax=ax, label="Forecast", color="red")
            ax.legend()
            st.pyplot(fig)

            st.write("🔮 Forecasted Sales:")
            st.write(forecast_series)

        except Exception as e:
            st.error(f"Error in forecasting: {e}")
    else:
        st.warning("Your dataset needs a 'Date' column for Forecasting.")
