import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
import os
import json
import ast
import base64
from utils import (
    load_category_data,
    analyze_category_aspects,
    create_aspect_category_matrix,
    get_csv_download_link
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
    
    # Create a bar chart of aspect counts by category
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Only include categories with aspects
    categories_with_data = sorted_categories[sorted_categories['aspectsCount'] > 0]
    
    # Create bars
    bars = ax.barh(categories_with_data['name'], categories_with_data['aspectsCount'])
    
    # Add labels and formatting
    ax.set_xlabel('Number of Aspects')
    ax.set_ylabel('Category')
    ax.set_title('Number of Aspects by Category')
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add the values at the end of each bar
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width + 0.3
        ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.0f}', 
                ha='left', va='center')
    
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
            ax.pie(type_counts['Count'], labels=type_counts['Type'], autopct='%1.1f%%',
                  startangle=90)
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            st.pyplot(fig)
        else:
            st.warning(f"The category '{selected_category}' has no aspects defined.")

# Tab 2: Aspect Usage Analysis
with tabs[1]:
    st.header("Which Aspects are Most/Least Used?")
    
    if analysis_results and 'aspect_freq' in analysis_results:
        aspect_freq = analysis_results['aspect_freq']
        
        # Top aspects visualization
        st.subheader("Most Used Aspects")
        
        # Create bar chart using Altair for the top 20 aspects
        top_n = min(20, len(aspect_freq))
        top_aspects = aspect_freq.head(top_n)
        
        chart = alt.Chart(top_aspects).mark_bar().encode(
            y=alt.Y('aspect:N', sort='-x', title='Aspect'),
            x=alt.X('count:Q', title='Number of Categories Using This Aspect'),
            tooltip=['aspect', 'count']
        ).properties(
            width=700,
            height=500,
            title=f'Top {top_n} Most Used Aspects Across Categories'
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        # Least used aspects
        st.subheader("Least Used Aspects")
        
        bottom_n = min(20, len(aspect_freq))
        bottom_aspects = aspect_freq.tail(bottom_n).sort_values('count')
        
        chart = alt.Chart(bottom_aspects).mark_bar().encode(
            y=alt.Y('aspect:N', sort='x', title='Aspect'),
            x=alt.X('count:Q', title='Number of Categories Using This Aspect'),
            tooltip=['aspect', 'count']
        ).properties(
            width=700,
            height=500,
            title=f'Top {bottom_n} Least Used Aspects Across Categories'
        )
        
        st.altair_chart(chart, use_container_width=True)
        
        # Distribution of aspect counts
        st.subheader("Distribution of Aspect Usage")
        
        # Create histogram of aspect counts
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(aspect_freq['count'], bins=20, alpha=0.7, color='blue')
        ax.set_xlabel('Number of Categories Using the Aspect')
        ax.set_ylabel('Number of Aspects')
        ax.set_title('Distribution of Aspect Usage')
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        st.pyplot(fig)
        
        # Create matrix visualization (heatmap)
        st.subheader("Aspect-Category Matrix")
        st.markdown("""
        This matrix shows which aspects (rows) are used in which categories (columns).
        Colored cells indicate that the aspect is used in that category.
        """)
        
        # Get the matrix
        matrix_df = create_aspect_category_matrix(category_data)
        
        if matrix_df is not None:
            # Only show first 20 aspects and categories for visibility
            max_aspects = 50
            max_categories = 20
            
            if len(matrix_df) > max_aspects:
                st.info(f"Showing only the first {max_aspects} aspects for clarity. Download the full matrix below.")
                
            if matrix_df.shape[1] - 1 > max_categories:  # -1 for the 'aspect' column
                # Select only the first max_categories categories
                cols_to_show = ['aspect'] + list(matrix_df.columns[1:max_categories+1])
                matrix_subset = matrix_df[cols_to_show]
            else:
                matrix_subset = matrix_df
                
            if len(matrix_subset) > max_aspects:
                matrix_subset = matrix_subset.head(max_aspects)
            
            # Convert to long format for Altair heatmap
            matrix_long = pd.melt(
                matrix_subset,
                id_vars=['aspect'],
                var_name='category',
                value_name='present'
            )
            
            # Create heatmap
            heatmap = alt.Chart(matrix_long).mark_rect().encode(
                x=alt.X('category:N', title='Category'),
                y=alt.Y('aspect:N', title='Aspect'),
                color=alt.Color('present:Q', scale=alt.Scale(domain=[0, 1], range=['white', 'blue'])),
                tooltip=['aspect', 'category', 'present']
            ).properties(
                width=1000,
                height=800,
                title='Aspect-Category Matrix'
            )
            
            st.altair_chart(heatmap, use_container_width=True)
            
            # Download the full matrix
            st.markdown("### Download Full Matrix")
            st.markdown(get_csv_download_link(matrix_df, "aspect_category_matrix.csv"), unsafe_allow_html=True)
    else:
        st.error("Analysis results are not available.")

# Tab 3: Categories without Aspects
with tabs[2]:
    st.header("Categories Without Aspects")
    
    if analysis_results and 'categories_no_aspects' in analysis_results:
        categories_no_aspects = analysis_results['categories_no_aspects']
        
        if not categories_no_aspects.empty:
            st.warning(f"Found {len(categories_no_aspects)} categories without any aspects defined:")
            
            # Display the categories without aspects
            st.dataframe(categories_no_aspects[['id', 'name', 'caCategoryId', 'createdAt', 'updatedAt']], use_container_width=True)
            
            # Create a download button for this data
            st.markdown("### Download List")
            st.markdown(get_csv_download_link(categories_no_aspects, "categories_without_aspects.csv"), unsafe_allow_html=True)
        else:
            st.success("All categories have aspects defined!")
    else:
        st.error("Analysis results are not available.")

# Tab 4: Raw Data
with tabs[3]:
    st.header("Raw Category Data")
    
    # Display the full dataset
    st.dataframe(category_data, use_container_width=True)
    
    # Download options
    st.markdown("### Download Data")
    st.markdown(get_csv_download_link(category_data, "category_data.csv"), unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Review Aspect Analyzer Tool - Category Analysis")