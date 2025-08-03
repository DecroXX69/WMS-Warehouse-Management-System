import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import glob
from datetime import datetime

class SKUMapper:
    def __init__(self):
        self.master_mapping = {}
        self.combo_mapping = {}
        self.inventory_data = None
        self.load_reference_data()

    def load_reference_data(self):
        """Load the three critical reference sheets from one Excel file"""
        try:
            excel_file = 'CSTE.xlsx'
            
            # Load all three sheets from the same Excel file
            msku_df = pd.read_excel(excel_file, sheet_name='Msku With Skus')
            combo_df = pd.read_excel(excel_file, sheet_name='Combos skus')
            inventory_df = pd.read_excel(excel_file, sheet_name='Current Inventory ')
            
            # Process MSKU mapping with correct column names
            sku_count = 0
            for _, row in msku_df.iterrows():
                sku = str(row.get('sku', '')).strip()
                msku = str(row.get('msku', '')).strip()
                
                if sku and msku and sku != 'nan' and msku != 'nan':
                    self.master_mapping[sku.upper()] = msku
                    sku_count += 1
                    if sku_count <= 5:
                        print(f"Mapped: {sku} -> {msku}")
            
            # Store combo information
            self.combo_mapping = combo_df.to_dict('records')
            
            # Store inventory data
            self.inventory_data = inventory_df
            
            print(f"✅ Loaded {len(self.master_mapping)} SKU mappings")
            print(f"✅ Loaded {len(self.combo_mapping)} combo products")
            print(f"✅ Loaded inventory data with {len(self.inventory_data)} items")
        
        except Exception as e:
            print(f"❌ Error loading reference data: {e}")
            print("Make sure your Excel file is in the same folder as this script")
            print("And check that the sheet names match exactly")

    def map_sku_to_msku(self, sku):
        """Map individual SKU to Master SKU"""
        sku_clean = str(sku).strip().upper()
        if sku_clean in self.master_mapping:
            return self.master_mapping[sku_clean]
        for mapped_sku, msku in self.master_mapping.items():
            if sku_clean in mapped_sku or mapped_sku in sku_clean:
                return msku
        return f"UNMAPPED_{sku_clean}"
    
    def process_sales_data(self, sales_file_path):
        """Process sales data and map SKUs to MSKUs - enhanced version"""
        try:
            # Check file extension and load accordingly
            if sales_file_path.lower().endswith('.csv'):
                sales_df = pd.read_csv(sales_file_path)
            else:
                sales_df = pd.read_excel(sales_file_path)
            
            # Check if MSKU column already exists (best case scenario)
            if 'MSKU' in sales_df.columns:
                print(f"✅ Found existing MSKU column in {sales_file_path} - using direct mapping!")
                sales_df['Mapped_MSKU'] = sales_df['MSKU']
                sales_df['Mapping_Status'] = 'DIRECT_MSKU'
                sku_column = 'MSKU'
            else:
                # Fall back to SKU mapping logic
                sku_column = None
                possible_sku_terms = ['sku', 'product', 'item', 'asin', 'fnsku', 'model', 'code', 'id', 'variant']
                
                for col in sales_df.columns:
                    col_lower = col.lower()
                    if any(term in col_lower for term in possible_sku_terms):
                        sku_column = col
                        break
                
                if not sku_column:
                    return None, f"Could not find SKU column. Available columns: {list(sales_df.columns)}"
                
                print(f"✅ Selected SKU column: '{sku_column}' for {sales_file_path}")
                
                # Apply mapping
                sales_df['Mapped_MSKU'] = sales_df[sku_column].apply(self.map_sku_to_msku)
                
                # Add mapping status
                sales_df['Mapping_Status'] = sales_df['Mapped_MSKU'].apply(
                    lambda x: 'MAPPED' if not x.startswith('UNMAPPED_') else 'UNMAPPED'
                )
            
            # Calculate statistics
            total_rows = len(sales_df)
            if 'MSKU' in sales_df.columns:
                mapped_rows = len(sales_df[sales_df['MSKU'].notna()])
                mapping_rate = (mapped_rows / total_rows) * 100 if total_rows > 0 else 0
            else:
                mapped_rows = len(sales_df[sales_df['Mapping_Status'] == 'MAPPED'])
                mapping_rate = (mapped_rows / total_rows) * 100 if total_rows > 0 else 0
            
            stats = {
                'total_skus': total_rows,
                'mapped_skus': mapped_rows,
                'unmapped_skus': total_rows - mapped_rows,
                'mapping_rate': mapping_rate
            }
            
            return sales_df, stats
            
        except Exception as e:
            return None, f"Error processing sales data: {e}"

class SKUMapperGUI:
    def __init__(self):
        self.mapper = SKUMapper()
        self.setup_gui()

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("WMS SKU Mapper")
        self.root.geometry("900x700")

        title_label = tk.Label(self.root, text="Warehouse Management System - SKU Mapper", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # File selection frame
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=20, padx=20, fill="x")

        tk.Label(file_frame, text="Select Sales Data File:", font=("Arial", 12)).pack(anchor="w")

        select_frame = tk.Frame(file_frame)
        select_frame.pack(fill="x", pady=5)

        self.file_path_var = tk.StringVar()
        self.file_entry = tk.Entry(select_frame, textvariable=self.file_path_var, width=60)
        self.file_entry.pack(side="left", fill="x", expand=True)

        browse_btn = tk.Button(select_frame, text="Browse", command=self.browse_file)
        browse_btn.pack(side="right", padx=(5, 0))

        # Button frame for both processing options
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)

        # Single file processing button
        process_btn = tk.Button(button_frame, text="Process Single File", command=self.process_data,
                                bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), pady=10, padx=20)
        process_btn.pack(side="left", padx=10)

        # Batch processing button
        batch_btn = tk.Button(button_frame, text="Process All CSV Files (Batch)", 
                             command=self.process_all_csv_files, bg="#2196F3", fg="white",
                             font=("Arial", 12, "bold"), pady=10, padx=20)
        batch_btn.pack(side="left", padx=10)

        # Results area
        results_frame = tk.Frame(self.root)
        results_frame.pack(pady=20, padx=20, fill="both", expand=True)

        tk.Label(results_frame, text="Results:", font=("Arial", 12, "bold")).pack(anchor="w")

        self.results_text = tk.Text(results_frame, height=20, wrap="word")
        scrollbar = tk.Scrollbar(results_frame, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)

        self.results_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Sales Data File",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)

    def process_data(self):
        """Process a single selected file"""
        file_path = self.file_path_var.get()

        if not file_path:
            messagebox.showerror("Error", "Please select a sales data file first!")
            return

        if not os.path.exists(file_path):
            messagebox.showerror("Error", "Selected file does not exist!")
            return

        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Processing sales data...\n\n")
        self.root.update()

        processed_data, result = self.mapper.process_sales_data(file_path)

        if processed_data is None:
            self.results_text.insert(tk.END, f"❌ Error: {result}\n")
            return

        stats = result
        self.results_text.insert(tk.END, "📊 PROCESSING RESULTS:\n")
        self.results_text.insert(tk.END, "=" * 50 + "\n")
        self.results_text.insert(tk.END, f"Total SKUs processed: {stats['total_skus']}\n")
        self.results_text.insert(tk.END, f"Successfully mapped: {stats['mapped_skus']}\n")
        self.results_text.insert(tk.END, f"Unmapped SKUs: {stats['unmapped_skus']}\n")
        self.results_text.insert(tk.END, f"Mapping success rate: {stats['mapping_rate']:.1f}%\n\n")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"processed_sales_data_{timestamp}.xlsx"
        processed_data.to_excel(output_file, index=False)

        self.results_text.insert(tk.END, f"✅ Processed data saved as: {output_file}\n\n")

        # Show unmapped SKUs if any
        unmapped = processed_data[processed_data['Mapping_Status'] == 'UNMAPPED']
        if len(unmapped) > 0:
            self.results_text.insert(tk.END, "⚠️ UNMAPPED SKUs (first 10):\n")
            self.results_text.insert(tk.END, "-" * 30 + "\n")

            sku_column = None
            for col in processed_data.columns:
                if any(term in col.lower() for term in ['sku', 'asin', 'fnsku']):
                    sku_column = col
                    break

            if sku_column:
                for idx, row in unmapped.head(10).iterrows():
                    self.results_text.insert(tk.END, f"• {row[sku_column]}\n")
            else:
                self.results_text.insert(tk.END, "Could not identify SKU column for display\n")

        messagebox.showinfo("Success", f"Processing complete!\nOutput saved as: {output_file}")

    def process_all_csv_files(self):
        """Process all CSV files in the current directory"""
        csv_files = glob.glob("*.csv")
        
        if not csv_files:
            messagebox.showwarning("Warning", "No CSV files found in current directory!")
            return
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"🚀 BATCH PROCESSING: Found {len(csv_files)} CSV files\n")
        self.results_text.insert(tk.END, "=" * 60 + "\n\n")
        
        summary_results = []
        all_processed_data = []
        
        for i, csv_file in enumerate(csv_files, 1):
            self.results_text.insert(tk.END, f"[{i}/{len(csv_files)}] Processing: {csv_file}\n")
            self.root.update()
            
            processed_data, result = self.mapper.process_sales_data(csv_file)
            
            if processed_data is not None:
                stats = result
                self.results_text.insert(tk.END, 
                    f"  ✅ Success: {stats['mapped_skus']}/{stats['total_skus']} mapped "
                    f"({stats['mapping_rate']:.1f}%)\n")
                
                # Save individual file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_filename = csv_file.replace('.csv', '').replace(' ', '_')
                output_file = f"processed_{clean_filename}_{timestamp}.xlsx"
                processed_data.to_excel(output_file, index=False)
                
                self.results_text.insert(tk.END, f"  📁 Saved as: {output_file}\n\n")
                
                # Store for combined file
                processed_data['Source_File'] = csv_file
                all_processed_data.append(processed_data)
                
                summary_results.append({
                    'file': csv_file,
                    'total': stats['total_skus'],
                    'mapped': stats['mapped_skus'],
                    'rate': stats['mapping_rate'],
                    'output': output_file
                })
            else:
                self.results_text.insert(tk.END, f"  ❌ Error: {result}\n\n")
        
        # Create combined file with all data
        if all_processed_data:
            combined_df = pd.concat(all_processed_data, ignore_index=True)
            combined_file = f"ALL_PROCESSED_SALES_DATA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Create multiple sheets in the combined file
            with pd.ExcelWriter(combined_file, engine='openpyxl') as writer:
                # All data in one sheet
                combined_df.to_excel(writer, sheet_name='All_Data', index=False)
                
                # Summary sheet
                summary_df = pd.DataFrame(summary_results)
                summary_df.to_excel(writer, sheet_name='Processing_Summary', index=False)
                
                # Individual file sheets
                for data in all_processed_data:
                    source_file = data['Source_File'].iloc[0].replace('.csv', '').replace(' ', '_')[:31]  # Excel sheet name limit
                    file_data = data.drop('Source_File', axis=1)
                    file_data.to_excel(writer, sheet_name=source_file, index=False)
            
            self.results_text.insert(tk.END, f"📊 COMBINED FILE CREATED: {combined_file}\n")
            self.results_text.insert(tk.END, f"📋 Contains {len(all_processed_data)} individual sheets + summary\n\n")
        
        # Final summary
        self.results_text.insert(tk.END, "🎯 BATCH PROCESSING SUMMARY:\n")
        self.results_text.insert(tk.END, "=" * 60 + "\n")
        
        total_processed = sum(r['total'] for r in summary_results)
        total_mapped = sum(r['mapped'] for r in summary_results)
        overall_rate = (total_mapped / total_processed * 100) if total_processed > 0 else 0
        
        for result in summary_results:
            self.results_text.insert(tk.END, 
                f"✅ {result['file']}: {result['rate']:.1f}% "
                f"({result['mapped']}/{result['total']})\n")
        
        self.results_text.insert(tk.END, f"\n🏆 OVERALL RESULTS:\n")
        self.results_text.insert(tk.END, f"   Total Files Processed: {len(summary_results)}\n")
        self.results_text.insert(tk.END, f"   Total SKUs Processed: {total_processed:,}\n")
        self.results_text.insert(tk.END, f"   Total SKUs Mapped: {total_mapped:,}\n")
        self.results_text.insert(tk.END, f"   Overall Success Rate: {overall_rate:.1f}%\n")
        
        messagebox.showinfo("Batch Processing Complete!", 
            f"✅ Successfully processed {len(summary_results)} CSV files\n"
            f"📊 Overall mapping rate: {overall_rate:.1f}%\n"
            f"📁 Combined file: {combined_file}\n"
            f"📈 Total SKUs processed: {total_processed:,}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    print("🚀 Starting WMS SKU Mapper...")
    print("Make sure your reference file is in the same folder:")
    print("  - CSTE.xlsx (with 3 sheets: 'Msku With Skus', 'Combos skus', 'Current Inventory ')")
    print("  - All your CSV files to be processed")
    print("\n" + "="*60)
    
    app = SKUMapperGUI()
    app.run()
