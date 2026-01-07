/**
 * CSV Exporter for SC4S Parser Data - Splunk lookup compatible
 */

class CSVExporter {
    constructor() {
        this.headers = [
            'parser_name',
            'parser_type',
            'vendor',
            'product',
            'file_path',
            'has_rewrites',
            'rewrite_count',
            'index',
            'sourcetype',
            'template',
            'class',
            'conditional_rewrites',
            'filter_programs',
            'filter_messages',
            'filter_hosts',
            'application_names',
            'application_types'
        ];
    }

    /**
     * Export data to CSV and trigger download
     * @param {Object} data - Parsed SC4S data with vendors hierarchy
     */
    exportToCSV(data) {
        if (!data || !data.vendors) {
            console.error('Invalid data for CSV export');
            return;
        }

        // Flatten data to rows
        const rows = this.flattenData(data);

        // Convert to CSV string
        const csv = this.toCSVString(rows);

        // Trigger download
        this.downloadCSV(csv);
    }

    /**
     * Flatten hierarchical data into rows
     * @param {Object} data - SC4S tree data
     * @returns {Array} Array of row objects
     */
    flattenData(data) {
        const rows = [];

        data.vendors.forEach(vendor => {
            vendor.products.forEach(product => {
                product.parsers.forEach(parser => {
                    const row = this.parserToRow(parser, vendor.name, product.name);
                    rows.push(row);
                });
            });
        });

        return rows;
    }

    /**
     * Convert parser to CSV row
     * @param {Object} parser - Parser definition
     * @param {string} vendor - Vendor name
     * @param {string} product - Product name
     * @returns {Object} Row object
     */
    parserToRow(parser, vendor, product) {
        // Calculate rewrite info
        const { hasRewrites, rewriteCount } = this.calculateRewriteInfo(parser);

        // Extract filters
        const filterPrograms = this.extractFilters(parser, 'program');
        const filterMessages = this.extractFilters(parser, 'message');
        const filterHosts = this.extractFilters(parser, 'host');

        // Extract applications
        const applicationNames = parser.applications
            ? parser.applications.map(app => app.name).join(';')
            : '';
        const applicationTypes = parser.applications
            ? parser.applications.map(app => app.type).join(';')
            : '';

        return {
            parser_name: parser.name || '',
            parser_type: parser.type || '',
            vendor: vendor || '',
            product: product || '',
            file_path: parser.file_path || '',
            has_rewrites: hasRewrites ? 'true' : 'false',
            rewrite_count: String(rewriteCount),
            index: parser.metadata?.index || '',
            sourcetype: parser.metadata?.sourcetype || '',
            template: parser.metadata?.template || '',
            class: parser.metadata?.class_ || '',
            conditional_rewrites: String(parser.conditional_rewrites?.length || 0),
            filter_programs: filterPrograms,
            filter_messages: filterMessages,
            filter_hosts: filterHosts,
            application_names: applicationNames,
            application_types: applicationTypes
        };
    }

    /**
     * Calculate rewrite information
     * @param {Object} parser - Parser definition
     * @returns {Object} Rewrite info { hasRewrites, rewriteCount }
     */
    calculateRewriteInfo(parser) {
        let rewriteCount = 0;

        // Check base metadata
        if (parser.metadata) {
            const hasMetadata = !!(
                parser.metadata.index ||
                parser.metadata.sourcetype ||
                parser.metadata.vendor ||
                parser.metadata.product ||
                parser.metadata.template ||
                parser.metadata.class_
            );

            if (hasMetadata) {
                rewriteCount += 1;
            }
        }

        // Add conditional rewrites
        if (parser.conditional_rewrites) {
            rewriteCount += parser.conditional_rewrites.length;
        }

        return {
            hasRewrites: rewriteCount > 0,
            rewriteCount: rewriteCount
        };
    }

    /**
     * Extract filters of specific type
     * @param {Object} parser - Parser definition
     * @param {string} filterType - Type of filter (program, message, host)
     * @returns {string} Semicolon-separated filter patterns
     */
    extractFilters(parser, filterType) {
        const patterns = [];

        if (parser.applications) {
            parser.applications.forEach(app => {
                if (app.filters) {
                    app.filters.forEach(filter => {
                        if (filter.type === filterType) {
                            patterns.push(filter.pattern);
                        }
                    });
                }
            });
        }

        return patterns.join(';');
    }

    /**
     * Convert rows to CSV string
     * @param {Array} rows - Array of row objects
     * @returns {string} CSV content
     */
    toCSVString(rows) {
        // Build header row
        const csvRows = [this.headers.join(',')];

        // Build data rows
        rows.forEach(row => {
            const values = this.headers.map(header => {
                const value = row[header] || '';
                return this.escapeCSVValue(value);
            });
            csvRows.push(values.join(','));
        });

        return csvRows.join('\n');
    }

    /**
     * Escape CSV value (handle quotes, commas, newlines)
     * @param {string} value - Value to escape
     * @returns {string} Escaped value
     */
    escapeCSVValue(value) {
        const stringValue = String(value);

        // If contains comma, quote, or newline, wrap in quotes and escape quotes
        if (stringValue.includes(',') ||
            stringValue.includes('"') ||
            stringValue.includes('\n')) {
            return '"' + stringValue.replace(/"/g, '""') + '"';
        }

        return stringValue;
    }

    /**
     * Trigger browser download of CSV file
     * @param {string} csv - CSV content
     */
    downloadCSV(csv) {
        // Create blob
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });

        // Create download link
        const link = document.createElement('a');

        if (link.download !== undefined) {
            // Generate filename with timestamp
            const timestamp = new Date().toISOString().split('T')[0];
            const filename = `sc4s_parsers_${timestamp}.csv`;

            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            console.log(`CSV exported: ${filename}`);
        } else {
            console.error('Browser does not support CSV download');
        }
    }
}
