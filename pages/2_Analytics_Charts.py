import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
import os
import glob
import json
import base64
from utils import (
    process_csv,
    analyze_aspects,
    get_csv_download_link,
    get_top_aspects,
    get_low_percentage_aspects,
    get_aspect_distribution,
    get_api_uploaded_files
)

# Page configuration
st.set_page_config(
    page_title="Analytics & Charts - Review Aspect Analyzer",
    page_icon="📊",
    layout="wide"
)

# App title and description
st.title("Analytics & Charts")
st.markdown("""
This page provides visual analytics and insights based on your review data.
""")

# Check if there's data available for analysis
if 'uploaded_data' not in st.session_state:
    st.warning("No data loaded for analysis. Please upload data from the Data Upload page first.")
    
    # Offer quick options to load data
    st.subheader("Quick Data Options")
    
    # Check for API uploads
    api_uploaded_files = get_api_uploaded_files()
    
    if api_uploaded_files:
        st.info(f"Found {len(api_uploaded_files)} files uploaded via API that you can use for analysis.")
        
        selected_api_file = st.selectbox(
            "Select an API-uploaded file:",
            options=api_uploaded_files,
            format_func=lambda x: os.path.basename(x)
        )
        
        if selected_api_file and st.button("Load Selected File"):
            with st.spinner("Loading data..."):
                df = process_csv(selected_api_file)
                if df is not None:
                    st.session_state['uploaded_data'] = df
                    st.success(f"Successfully loaded {len(df)} reviews!")
                    st.rerun()
    
    # Option to upload file directly here
    st.markdown("Or upload a file directly:")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    
    if uploaded_file is not None:
        with st.spinner("Processing uploaded file..."):
            df = process_csv(uploaded_file)
            if df is not None:
                st.session_state['uploaded_data'] = df
                st.success(f"Successfully loaded {len(df)} reviews!")
                st.rerun()
    
    st.markdown("[Go to Data Upload Page](/Data_Upload)")
    st.stop()

# At this point, we have data in the session state
df = st.session_state['uploaded_data']

# Display basic data information
st.subheader("Data Overview")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Reviews", len(df))
with col2:
    st.metric("Categories", df['category'].nunique())
with col3:
    # Count unique aspects
    unique_aspects = set()
    for aspects in df['aspects_list']:
        unique_aspects.update(aspects)
    st.metric("Unique Aspects", len(unique_aspects))
with col4:
    # Calculate average aspects per review
    avg_aspects = sum(len(aspects) for aspects in df['aspects_list']) / len(df)
    st.metric("Avg Aspects/Review", f"{avg_aspects:.2f}")

# Analyze the data
analysis_df, pivot_df = analyze_aspects(df)

# Create tabs for different analytics views
tabs = st.tabs([
    "Aspect Distribution", 
    "Aspect Analysis", 
    "Category Insights", 
    "Underrepresented Aspects",
    "Data Export"
])

# Tab 1: Aspect Distribution
with tabs[0]:
    st.header("Aspect Distribution by Category")
    
    if pivot_df is not None:
        # Get categories for filtering
        categories = df['category'].unique()
        
        # Allow filtering by category
        selected_category = st.selectbox(
            "Filter by Category", 
            options=["All Categories"] + list(categories)
        )
        
        if selected_category == "All Categories":
            # Show a heatmap of all aspects across categories
            st.subheader("Aspect Heatmap")
            
            # Prepare data for heatmap using Altair
            # Melt the pivot table to get it in the right format for Altair
            melted_pivot = pivot_df.melt(
                id_vars=['aspect'],
                var_name='category',
                value_name='percentage'
            )
            
            # Create the heatmap
            heatmap = alt.Chart(melted_pivot).mark_rect().encode(
                x=alt.X('category:N', title='Category'),
                y=alt.Y('aspect:N', title='Aspect'),
                color=alt.Color('percentage:Q', title='Percentage', scale=alt.Scale(scheme='viridis')),
                tooltip=['category', 'aspect', alt.Tooltip('percentage:Q', title='Percentage', format='.2f')]
            ).properties(
                width=700,
                height=500,
                title='Aspect Distribution across Categories'
            )
            
            st.altair_chart(heatmap, use_container_width=True)
            
            # Also show top aspects overall
            st.subheader("Top Aspects Overall")
            top_aspects = get_top_aspects(analysis_df)
            
            if top_aspects is not None:
                # Create bar chart for top aspects
                bars = alt.Chart(top_aspects).mark_bar().encode(
                    x=alt.X('count:Q', title='Count'),
                    y=alt.Y('aspect:N', title='Aspect', sort='-x'),
                    tooltip=['aspect', 'count']
                ).properties(
                    width=600,
                    height=400,
                    title='Top Aspects by Frequency'
                )
                
                st.altair_chart(bars, use_container_width=True)
        else:
            # Filter for the selected category
            category_data = analysis_df[analysis_df['category'] == selected_category]
            
            # Show distribution for the selected category
            st.subheader(f"Aspect Distribution for {selected_category}")
            
            # Sort by percentage
            category_data = category_data.sort_values('percentage', ascending=False)
            
            # Create bar chart
            fig, ax = plt.subplots(figsize=(12, 8))
            bars = ax.bar(category_data['aspect'], category_data['percentage'])
            
            # Color the bars based on percentage threshold
            for i, bar in enumerate(bars):
                if category_data.iloc[i]['is_low_percentage']:
                    bar.set_color('red')
                else:
                    bar.set_color('blue')
            
            # Add labels and formatting
            ax.set_xlabel('Aspect')
            ax.set_ylabel('Percentage (%)')
            ax.set_title(f'Aspect Distribution for {selected_category}')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Add a horizontal line at 5%
            ax.axhline(y=5, color='r', linestyle='--', alpha=0.5)
            ax.text(0, 5.2, '5% Threshold', color='r')
            
            st.pyplot(fig)
            
            # Also show the same data in a table
            st.subheader("Aspects Data Table")
            # Format percentage column for display
            display_df = category_data.copy()
            display_df['percentage'] = display_df['percentage'].round(2).astype(str) + '%'
            st.dataframe(display_df[['aspect', 'count', 'total_reviews', 'percentage']])
    else:
        st.error("No analysis data available. Please check that your data is properly formatted.")

# Tab 2: Aspect Analysis
with tabs[1]:
    st.header("Aspect Analysis")
    
    if analysis_df is not None:
        # Get unique aspects for selection
        all_aspects = analysis_df['aspect'].unique()
        
        # Allow selecting an aspect to analyze
        selected_aspect = st.selectbox(
            "Select an Aspect to Analyze",
            options=all_aspects
        )
        
        if selected_aspect:
            # Filter data for the selected aspect
            aspect_data = analysis_df[analysis_df['aspect'] == selected_aspect]
            
            # Show distribution across categories
            st.subheader(f"Distribution of '{selected_aspect}' Across Categories")
            
            # Sort by percentage
            aspect_data = aspect_data.sort_values('percentage', ascending=False)
            
            # Create bar chart
            chart = alt.Chart(aspect_data).mark_bar().encode(
                x=alt.X('category:N', title='Category'),
                y=alt.Y('percentage:Q', title='Percentage (%)'),
                color=alt.condition(
                    alt.datum.is_low_percentage == True,
                    alt.value('red'),
                    alt.value('blue')
                ),
                tooltip=['category', 'count', 'total_reviews', alt.Tooltip('percentage:Q', format='.2f')]
            ).properties(
                width=600,
                height=400,
                title=f"Distribution of '{selected_aspect}' Across Categories"
            )
            
            # Add a horizontal rule for the 5% threshold
            rule = alt.Chart().mark_rule(color='red', strokeDash=[3, 3]).encode(
                y='threshold:Q'
            ).transform_calculate(
                threshold='5'
            )
            
            st.altair_chart(chart + rule, use_container_width=True)
            
            # Show aspect statistics
            st.subheader("Aspect Statistics")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Mentions", aspect_data['count'].sum())
            with col2:
                avg_pct = aspect_data['percentage'].mean()
                st.metric("Average Percentage", f"{avg_pct:.2f}%")
            with col3:
                low_count = aspect_data[aspect_data['is_low_percentage']].shape[0]
                st.metric("Categories Below 5%", low_count)
            
            # Show the data table
            st.subheader("Data Table")
            # Format percentage column for display
            display_df = aspect_data.copy()
            display_df['percentage'] = display_df['percentage'].round(2).astype(str) + '%'
            st.dataframe(display_df[['category', 'count', 'total_reviews', 'percentage']])
    else:
        st.error("No analysis data available. Please check that your data is properly formatted.")

# Tab 3: Category Insights
with tabs[2]:
    st.header("Category Insights")
    
    if analysis_df is not None:
        # Get categories
        categories = df['category'].unique()
        
        # Get aspect distribution by category
        category_aspect_counts = get_aspect_distribution(analysis_df)
        
        if category_aspect_counts is not None:
            # Show category comparison
            st.subheader("Category Comparison")
            
            # Create bar chart of aspects per category
            bars = alt.Chart(category_aspect_counts).mark_bar().encode(
                x=alt.X('category:N', title='Category'),
                y=alt.Y('unique_aspects:Q', title='Number of Unique Aspects'),
                tooltip=['category', 'unique_aspects']
            ).properties(
                width=600,
                height=400,
                title='Number of Unique Aspects by Category'
            )
            
            st.altair_chart(bars, use_container_width=True)
            
            # Calculate review counts by category
            review_counts = df.groupby('category').size().reset_index(name='review_count')
            
            # Combine with aspect counts
            category_stats = pd.merge(
                category_aspect_counts,
                review_counts,
                on='category'
            )
            
            # Calculate aspects per review
            category_stats['aspects_per_review'] = category_stats['unique_aspects'] / category_stats['review_count']
            
            # Show category statistics
            st.subheader("Category Statistics")
            st.dataframe(category_stats.sort_values('unique_aspects', ascending=False))
            
            # Allow comparing two categories
            st.subheader("Compare Categories")
            
            col1, col2 = st.columns(2)
            with col1:
                category1 = st.selectbox(
                    "First Category", 
                    options=categories,
                    key="cat1"
                )
            with col2:
                remaining_categories = [c for c in categories if c != category1]
                category2 = st.selectbox(
                    "Second Category", 
                    options=remaining_categories,
                    key="cat2"
                )
            
            if category1 and category2:
                # Get aspects for both categories
                aspects_cat1 = set(analysis_df[analysis_df['category'] == category1]['aspect'])
                aspects_cat2 = set(analysis_df[analysis_df['category'] == category2]['aspect'])
                
                # Find common and unique aspects
                common_aspects = aspects_cat1.intersection(aspects_cat2)
                unique_to_cat1 = aspects_cat1 - aspects_cat2
                unique_to_cat2 = aspects_cat2 - aspects_cat1
                
                # Display the comparison
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"### Unique to {category1}")
                    st.write(f"**Count:** {len(unique_to_cat1)}")
                    for aspect in sorted(unique_to_cat1):
                        st.write(f"- {aspect}")
                
                with col2:
                    st.markdown("### Common Aspects")
                    st.write(f"**Count:** {len(common_aspects)}")
                    for aspect in sorted(common_aspects):
                        st.write(f"- {aspect}")
                
                with col3:
                    st.markdown(f"### Unique to {category2}")
                    st.write(f"**Count:** {len(unique_to_cat2)}")
                    for aspect in sorted(unique_to_cat2):
                        st.write(f"- {aspect}")
    else:
        st.error("No analysis data available. Please check that your data is properly formatted.")

# Tab 4: Underrepresented Aspects
with tabs[3]:
    st.header("Underrepresented Aspects")
    
    if analysis_df is not None:
        # Get low percentage aspects
        low_percentage_aspects = get_low_percentage_aspects(analysis_df)
        
        if low_percentage_aspects is not None and not low_percentage_aspects.empty:
            st.subheader("Aspects Below 5% Threshold")
            st.markdown("""
            These aspects appear in less than 5% of reviews for their respective categories.
            They may represent:
            - Emerging issues or features
            - Rarely mentioned but important aspects
            - Potential gaps in your review collection process
            """)
            
            # Format percentage for display
            display_df = low_percentage_aspects.copy()
            display_df['percentage'] = display_df['percentage'].round(2).astype(str) + '%'
            
            # Show the low percentage aspects
            st.dataframe(
                display_df[['category', 'aspect', 'count', 'total_reviews', 'percentage']],
                use_container_width=True
            )
            
            # Visualize with a scatter plot
            st.subheader("Visualization of Low Percentage Aspects")
            
            # Create scatter plot of low percentage aspects
            scatter = alt.Chart(low_percentage_aspects).mark_circle(size=100).encode(
                x=alt.X('percentage:Q', title='Percentage (%)'),
                y=alt.Y('category:N', title='Category'),
                color='category:N',
                size='count:Q',
                tooltip=['category', 'aspect', 'count', 'total_reviews', alt.Tooltip('percentage:Q', format='.2f')]
            ).properties(
                width=700,
                height=400,
                title='Low Percentage Aspects (<5%) by Category'
            ).interactive()
            
            st.altair_chart(scatter, use_container_width=True)
            
            # Group by category and count
            category_counts = low_percentage_aspects.groupby('category').size().reset_index(name='low_aspect_count')
            
            # Visualize categories with most low percentage aspects
            st.subheader("Categories with Most Underrepresented Aspects")
            
            bars = alt.Chart(category_counts).mark_bar().encode(
                x=alt.X('low_aspect_count:Q', title='Number of Aspects < 5%'),
                y=alt.Y('category:N', title='Category', sort='-x'),
                tooltip=['category', 'low_aspect_count']
            ).properties(
                width=600,
                height=400,
                title='Categories with Most Underrepresented Aspects'
            )
            
            st.altair_chart(bars, use_container_width=True)
        else:
            st.success("No aspects below the 5% threshold were found in your data. Good job!")
    else:
        st.error("No analysis data available. Please check that your data is properly formatted.")

# Tab 5: Data Export
with tabs[4]:
    st.header("Export Analysis")
    
    if analysis_df is not None and pivot_df is not None:
        st.markdown("""
        Export your analysis data in various formats for further processing or reporting.
        """)
        
        # Choose export format
        export_type = st.radio(
            "Select export format:",
            ["Aspect Analysis Table", "Pivot Table (Aspects by Category)", "Low Percentage Aspects Only"]
        )
        
        if export_type == "Aspect Analysis Table":
            export_df = analysis_df.copy()
            
            # Format percentage for display
            export_df['percentage'] = export_df['percentage'].round(2)
            
            # Select columns for export
            export_columns = st.multiselect(
                "Select columns to include in export:",
                options=export_df.columns.tolist(),
                default=['category', 'aspect', 'count', 'total_reviews', 'percentage', 'is_low_percentage']
            )
            
            filename = "aspect_analysis.csv"
            
        elif export_type == "Pivot Table (Aspects by Category)":
            export_df = pivot_df.copy()
            filename = "aspect_pivot_table.csv"
            
            # No column selection for pivot table
            export_columns = export_df.columns.tolist()
            
        else:  # Low percentage aspects
            low_percentage_aspects = get_low_percentage_aspects(analysis_df)
            
            if low_percentage_aspects is not None and not low_percentage_aspects.empty:
                export_df = low_percentage_aspects.copy()
                
                # Format percentage for display
                export_df['percentage'] = export_df['percentage'].round(2)
                
                # Select columns for export
                export_columns = st.multiselect(
                    "Select columns to include in export:",
                    options=export_df.columns.tolist(),
                    default=['category', 'aspect', 'count', 'total_reviews', 'percentage']
                )
                
                filename = "low_percentage_aspects.csv"
            else:
                st.warning("No low percentage aspects found in the data.")
                export_df = None
                export_columns = []
        
        # Preview the export data
        if export_df is not None and len(export_columns) > 0:
            st.subheader("Export Preview")
            st.dataframe(export_df[export_columns].head(10))
            
            # Generate download link
            if st.button("Generate Export"):
                export_csv = export_df[export_columns].to_csv(index=False)
                b64 = base64.b64encode(export_csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download {filename}</a>'
                st.markdown(href, unsafe_allow_html=True)
    else:
        st.error("No analysis data available. Please check that your data is properly formatted.")

# Footer
st.markdown("---")
st.caption("Review Aspect Analyzer Tool v1.0")