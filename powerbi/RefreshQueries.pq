// Create a text parameter named DataFolder first. Disable load for this query.
// Replace each existing CSV query's Advanced Editor with, for example:
// let Source = RefreshQueries[fact_orders] in Source
// These replacements are NOT embedded in the existing PBIX until applied in Desktop.
let
    ReadCsv = (name as text, types as list) as table =>
        let
            Path = Text.TrimEnd(DataFolder, {"/", "\"}) & "/" & name & ".csv",
            Source = Csv.Document(File.Contents(Path), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
            Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
            Required = List.Transform(types, each _{0}),
            Missing = List.Difference(Required, Table.ColumnNames(Headers)),
            Checked = if List.IsEmpty(Missing) then Headers else error Error.Record("Schema mismatch", name, Missing),
            // Python exports month keys as YYYY-MM; avoid locale-dependent parsing.
            MonthColumns = List.Intersect({{"purchase_month", "year_month"}, Table.ColumnNames(Checked)}),
            Months = Table.TransformColumns(Checked, List.Transform(MonthColumns, (column) => {column, each if _ = null or _ = "" then null else Date.FromText(Text.Start(_, 7) & "-01", [Format="yyyy-MM-dd", Culture="en-US"]), type date})),
            Typed = Table.TransformColumnTypes(Months, types, "en-US")
        in Typed,
    Orders = ReadCsv("fact_orders", {{"order_id", type text}, {"customer_id", type text}, {"order_status", type text}, {"order_purchase_timestamp", type datetime}, {"order_approved_at", type datetime}, {"order_delivered_carrier_date", type datetime}, {"order_delivered_customer_date", type datetime}, {"order_estimated_delivery_date", type date}, {"customer_unique_id", type text}, {"customer_zip_code_prefix", Int64.Type}, {"customer_city", type text}, {"customer_state", type text}, {"item_gmv", type number}, {"freight_value", type number}, {"item_count", Int64.Type}, {"seller_count", Int64.Type}, {"category_count", Int64.Type}, {"amount_paid", type number}, {"max_installments", Int64.Type}, {"payment_method_count", Int64.Type}, {"primary_payment_type", type text}, {"review_score", type number}, {"review_count", Int64.Type}, {"purchase_date", type date}, {"purchase_month", type date}, {"delivery_days", type number}, {"delay_days", type number}, {"late_flag", Int64.Type}, {"on_time_flag", Int64.Type}, {"low_review_flag", Int64.Type}, {"is_delivered", Int64.Type}, {"freight_to_item_value", type number}, {"customer_delivered_order_number", Int64.Type}, {"first_observed_delivered_order_flag", Int64.Type}}),
    Sales = ReadCsv("fact_sales", {{"order_id", type text}, {"order_item_id", Int64.Type}, {"product_id", type text}, {"seller_id", type text}, {"shipping_limit_date", type datetime}, {"price", type number}, {"freight_value", type number}, {"product_category_name_english", type text}, {"customer_unique_id", type text}, {"order_status", type text}, {"purchase_date", type date}, {"purchase_month", type date}, {"customer_state", type text}, {"on_time_flag", Int64.Type}, {"late_flag", Int64.Type}, {"review_score", type number}, {"low_review_flag", Int64.Type}, {"primary_payment_type", type text}, {"max_installments", Int64.Type}}),
    // Preserve existing model references while removing the CSV header from the rows.
    Customers = Table.RenameColumns(ReadCsv("dim_customer", {{"customer_unique_id", type text}, {"customer_city", type text}, {"customer_state", type text}}), {{"customer_unique_id", "Column1"}, {"customer_city", "Column2"}, {"customer_state", "State"}}),
    Products = ReadCsv("dim_product", {{"product_id", type text}, {"product_category_name_english", type text}, {"product_name_lenght", Int64.Type}, {"product_description_lenght", Int64.Type}, {"product_photos_qty", Int64.Type}, {"product_weight_g", Int64.Type}, {"product_length_cm", Int64.Type}, {"product_height_cm", Int64.Type}, {"product_width_cm", Int64.Type}}),
    Sellers = ReadCsv("dim_seller", {{"seller_id", type text}, {"seller_zip_code_prefix", Int64.Type}, {"seller_city", type text}, {"seller_state", type text}}),
    Dates = ReadCsv("dim_date", {{"date", type date}, {"date_key", Int64.Type}, {"year", Int64.Type}, {"quarter", type text}, {"month_number", Int64.Type}, {"month_name", type text}, {"year_month", type date}, {"week_of_year", Int64.Type}, {"day_of_week", type text}}),
    RFM = ReadCsv("mart_customer_rfm", {{"customer_unique_id", type text}, {"first_purchase", type datetime}, {"last_purchase", type datetime}, {"frequency", Int64.Type}, {"observed_gmv", type number}, {"recency_days", Int64.Type}, {"segment", type text}, {"high_value_threshold_brl", type number}})
in
    [fact_orders=Orders, fact_sales=Sales, dim_customer=Customers, dim_product=Products, dim_seller=Sellers, dim_date=Dates, mart_customer_rfm=RFM]
