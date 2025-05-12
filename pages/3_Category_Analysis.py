import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
from utils import (
    load_category_data,
    analyze_category_aspects,
    create_aspect_category_matrix,
    get_csv_download_link,
    get_json_download_link
)

# Page configuration
st.set_page_config(
    page_title="Category Analysis - Review Aspect Analyzer",
    page_icon="📊",
    layout="wide"
)

# App title and description
st.title("Category & Aspect Analysis")
st.markdown("""
This page provides analytics specifically for review categories and their aspects,
based on data from the internal API.
""")

# Load the category data
category_data = load_category_data()

if category_data is None:
    st.error("Failed to load category data. Please check the file path and format.")
    st.stop()

# Display some basic stats
total_categories = len(category_data)
categories_with_aspects = len(category_data[category_data['aspectsCount'] > 0])
categories_without_aspects = total_categories - categories_with_aspects

# Create a summary section
st.header("Summary Statistics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Categories", total_categories)
with col2:
    st.metric("Categories with Aspects", categories_with_aspects)
with col3:
    st.metric("Categories without Aspects", categories_without_aspects)
with col4:
    avg_aspects = category_data['aspectsCount'].mean()
    st.metric("Avg Aspects per Category", f"{avg_aspects:.1f}")

# Create tabs for different analysis views
tabs = st.tabs([
    "Aspect Distribution by Category", 
    "Aspect Usage Analysis", 
    "Categories without Aspects", 
    "Raw Data"
])

# Analyze the data
analysis_results = analyze_category_aspects(category_data)

# Tab 1: Aspect Distribution by Category
with tabs[0]:
    st.header("What Aspects are in Each Category?")
    
    # Sort categories by aspect count
    sorted_categories = category_data.sort_values('aspectsCount', ascending=False)
    
    # Create a bar chart of aspect counts by category with dynamic sizing
    # Calculate the figure height based on number of categories (minimum 10, with 0.4 units per category)
    num_categories = len(sorted_categories[sorted_categories['aspectsCount'] > 0])
    figure_height = max(10, num_categories * 0.4)  # Dynamic height with minimum of 10
    
    fig, ax = plt.subplots(figsize=(12, figure_height))
    
    # Only include categories with aspects
    categories_with_data = sorted_categories[sorted_categories['aspectsCount'] > 0]
    
    # Create bars
    bars = ax.barh(categories_with_data['name'], categories_with_data['aspectsCount'])
    
    # Add labels and formatting
    ax.set_xlabel('Number of Aspects')
    ax.set_ylabel('Category')
    ax.set_title('Number of Aspects by Category', fontsize=16)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add the values at the end of each bar
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width + 0.3
        ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.0f}', 
                ha='left', va='center')
                
    # Adjust layout and margins
    plt.tight_layout()
    plt.subplots_adjust(left=0.25)  # Add more space for category names
    
    st.pyplot(fig)
    
    # Allow exploring specific categories and their aspects
    st.subheader("Explore Category Aspects")
    selected_category = st.selectbox(
        "Select a category to see its aspects:",
        options=category_data['name'].tolist()
    )
    
    if selected_category:
        category_row = category_data[category_data['name'] == selected_category].iloc[0]
        aspect_list = category_row['aspects_parsed']
        
        if aspect_list:
            st.success(f"The category '{selected_category}' has {len(aspect_list)} aspects:")
            
            # Display aspects in a more readable format
            aspects_df = pd.DataFrame({
                'Aspect': aspect_list,
                'Type': [aspect.split('/')[0] if '/' in aspect else 'Other' for aspect in aspect_list],
                'Subtype': [aspect.split('/')[1] if '/' in aspect else aspect for aspect in aspect_list]
            })
            
            # Group by type and display
            st.dataframe(aspects_df, use_container_width=True)

            # Create a pie chart showing the distribution of aspect types
            type_counts = aspects_df['Type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Count']

            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(type_counts['Count'], labels=type_counts['Type'].tolist(), autopct='%1.1f%%',
                   startangle=90)
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            st.pyplot(fig)
        else:
            st.warning(f"The category '{selected_category}' has no aspects defined.")

# Tab 2: Aspect Usage Analysis
with tabs[1]:
    st.header("Which Aspects are Most/Least Used?")

    # `analyze_category_aspects()` returns a DataFrame, not a dict
    if analysis_results is not None and isinstance(analysis_results, pd.DataFrame):
        aspect_freq: pd.DataFrame = analysis_results.copy()

        # ────────────────────────────────────────────────────────────────────
        # Most-used aspects
        # ────────────────────────────────────────────────────────────────────
        st.subheader("Most Used Aspects")

        top_n = min(20, len(aspect_freq))
        top_aspects = aspect_freq.head(top_n)

        alt_data = alt.Data(values=top_aspects.to_dict("records"))
        top_chart = (
            alt.Chart(alt_data)
            .mark_bar()
            .encode(
                y=alt.Y("aspect:N", sort="-x", title="Aspect"),
                x=alt.X("count:Q", title="Number of Categories Using This Aspect"),
                tooltip=["aspect:N", "count:Q"],
            )
            .properties(width=700, height=500, title=f"Top {top_n} Most Used Aspects Across Categories")
        )
        st.altair_chart(top_chart, use_container_width=True)

        # ────────────────────────────────────────────────────────────────────
        # Least-used aspects
        # ────────────────────────────────────────────────────────────────────
        st.subheader("Least Used Aspects")

        bottom_n = min(20, len(aspect_freq))
        bottom_aspects = aspect_freq.sort_values(by="count", ascending=True).head(bottom_n)

        alt_data = alt.Data(values=bottom_aspects.to_dict("records"))
        bottom_chart = (
            alt.Chart(alt_data)
            .mark_bar()
            .encode(
                y=alt.Y("aspect:N", sort="x", title="Aspect"),
                x=alt.X("count:Q", title="Number of Categories Using This Aspect"),
                tooltip=["aspect:N", "count:Q"],
            )
            .properties(width=700, height=500, title=f"Top {bottom_n} Least Used Aspects Across Categories")
        )
        st.altair_chart(bottom_chart, use_container_width=True)

        # ────────────────────────────────────────────────────────────────────
        # Distribution histogram with enhancements
        # ────────────────────────────────────────────────────────────────────
        st.subheader("Distribution of Aspect Usage")

        # Extract data
        counts = aspect_freq["count"].to_numpy()

        # Summary stats
        mean_val = np.mean(counts)
        median_val = np.median(counts)

        fig, ax = plt.subplots(figsize=(10, 6))

        # Histogram
        ax.hist(counts, bins=20, alpha=0.7, color='steelblue', edgecolor='black')

        # Labels
        ax.set_xlabel("Number of Categories Using the Aspect")
        ax.set_ylabel("Number of Aspects")
        ax.set_title("How Widely Aspects Are Used Across Categories")

        # Gridlines
        ax.grid(axis="y", linestyle="--", alpha=0.7)

        # Add mean and median lines
        ax.axvline(mean_val, color='red', linestyle='dashed', linewidth=1.5, label=f'Mean: {mean_val:.1f}')
        ax.axvline(median_val, color='green', linestyle='dotted', linewidth=1.5, label=f'Median: {median_val:.1f}')

        # Annotate histogram with explanation
        st.markdown("""
        This chart shows **how widely aspects are used across different categories**:

        - **Left side** (low values): Aspects that are niche — used in only a few categories.
        - **Right side** (high values): Aspects that are universal — used in many or all categories.
        - The **red dashed line** is the mean usage, and the **green dotted line** is the median.

        Use this chart to understand whether your aspects are generally broad or specific.
        """)

        # Legend
        ax.legend()

        # Show chart
        st.pyplot(fig)

        # ────────────────────────────────────────────────────────────────────
        # Aspect-Category matrix
        # ────────────────────────────────────────────────────────────────────
        st.subheader("Aspect-Category Matrix")
        st.markdown(
            """
            This matrix shows which aspects (rows) are used in which categories (columns).
            Colored cells indicate that the aspect is used in that category.
            """
        )

        matrix_df = create_aspect_category_matrix(category_data)

        if matrix_df is not None and isinstance(matrix_df, pd.DataFrame):
            max_aspects, max_categories = 500, 500

            if len(matrix_df) > max_aspects:
                st.info(
                    f"Showing only the first {max_aspects} aspects for clarity. "
                    "Download the full matrix below."
                )

            # Trim to first N categories (after the 'aspect' column)
            visible_cols = ["aspect"] + list(matrix_df.columns[1 : max_categories + 1])
            matrix_subset = matrix_df.loc[:, visible_cols].head(max_aspects)

            # Reshape for Altair
            matrix_long = pd.melt(
                matrix_subset,
                id_vars=["aspect"],
                var_name="category",
                value_name="present",
                ignore_index=False,
            )

            alt_data = alt.Data(values=matrix_long.to_dict("records"))
            heatmap = (
                alt.Chart(alt_data)
                .mark_rect()
                .encode(
                    x=alt.X("category:N", title="Category"),
                    y=alt.Y("aspect:N", title="Aspect"),
                    color=alt.Color(
                        "present:Q",
                        scale=alt.Scale(domain=[0, 1], range=["white", "blue"]),
                    ),
                    tooltip=["aspect:N", "category:N", "present:Q"],
                )
                .properties(width=1000, height=800, title="Aspect-Category Matrix")
            )
            st.altair_chart(heatmap, use_container_width=True)

            # ────────────────────────────────────────────────────────────
            # Download links
            # ────────────────────────────────────────────────────────────
            st.markdown("### Download Full Matrix")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    get_csv_download_link(matrix_df, "aspect_category_matrix.csv"),
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    get_json_download_link(matrix_df, "aspect_category_matrix.json"),
                    unsafe_allow_html=True,
                )
    else:
        st.warning("Analysis results are not available. Please run the analysis first.")
# Tab 3: Categories without Aspects
with tabs[2]:
    st.header("Categories Without Aspects")

    if analysis_results is not None:
        # Filter categories without aspects
        categories_no_aspects_df = category_data[category_data['aspectsCount'] == 0]

        # Display the actual categories without aspects
        if not categories_no_aspects_df.empty:
            st.subheader("Categories Without Aspects (Details)")
            st.write(f"Found {len(categories_no_aspects_df)} categories without aspects defined:")
            st.dataframe(categories_no_aspects_df, use_container_width=True)
        else:
            st.success("All categories have aspects.")

# Tab 4: Raw Data
with tabs[3]:
    st.header("Raw Category Data")
    
    # Display the full dataset
    st.dataframe(category_data, use_container_width=True)
    
    # Download options
    st.markdown("### Download Data")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(get_csv_download_link(category_data, "category_data.csv"), unsafe_allow_html=True)
    with col2:
        st.markdown(get_json_download_link(category_data, "category_data.json"), unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Review Aspect Analyzer Tool - Category Analysis")