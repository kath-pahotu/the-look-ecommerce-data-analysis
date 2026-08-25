// Create a Text parameter named pDataFolder that points to:
// <project>\data\processed\power_bi\csv

// Function query: fnLoadCsv
(fileName as text) as table =>
let
    Source = Csv.Document(
        File.Contents(pDataFolder & "\\" & fileName & ".csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    PromotedHeaders

// Example table query:
// let Source = fnLoadCsv("fact_order_item") in Source

// Set types explicitly in each query after loading.
