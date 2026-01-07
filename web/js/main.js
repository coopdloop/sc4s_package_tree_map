/**
 * SC4S Parser Tree Visualizer - Main Application
 */

// Global instances
let dataLoader;
let treeVisualizer;
let detailPanel;
let searchEngine;
let csvExporter;

// Initialize application
document.addEventListener('DOMContentLoaded', async function() {
    console.log('SC4S Parser Tree Visualizer - Initializing...');

    try {
        // Initialize components
        dataLoader = new DataLoader();
        detailPanel = new DetailPanel('detail-panel');

        // Show loading state
        showLoading();

        // Load data
        await dataLoader.load();

        // Initialize tree visualizer
        treeVisualizer = new TreeVisualizer('tree-container', detailPanel);

        // Initialize search engine
        const parsers = dataLoader.getParsersFlat();
        searchEngine = new SearchEngine(parsers, treeVisualizer, detailPanel);

        // Initialize CSV exporter
        csvExporter = new CSVExporter();

        // Render initial view
        const viewData = dataLoader.getViewData('vendor');
        treeVisualizer.render(viewData);

        // Update footer stats
        updateFooter(dataLoader.getMetadata());

        // Setup event listeners
        setupEventListeners();

        // Hide loading state
        hideLoading();

        console.log('Application initialized successfully');

    } catch (error) {
        console.error('Failed to initialize application:', error);
        showError(error);
    }
});

function setupEventListeners() {
    // Search box - debounce for full search results
    const searchBox = document.getElementById('search');
    if (searchBox) {
        let searchTimeout;
        searchBox.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            // Only trigger full search after user stops typing
            searchTimeout = setTimeout(() => {
                if (e.target.value.length >= 2) {
                    searchEngine.search(e.target.value);
                } else if (e.target.value.length === 0) {
                    searchEngine.clearResults();
                    searchEngine.treeVisualizer.clearHighlights();
                }
            }, 500); // Debounce 500ms to give autocomplete priority
        });
    }

    // View mode selector
    const viewMode = document.getElementById('view-mode');
    if (viewMode) {
        viewMode.addEventListener('change', function(e) {
            switchView(e.target.value);
        });
    }

    // Layout mode selector
    const layoutMode = document.getElementById('layout-mode');
    if (layoutMode) {
        layoutMode.addEventListener('change', function(e) {
            switchLayout(e.target.value);
        });
    }

    // Expand/collapse all buttons
    const expandAllBtn = document.getElementById('expand-all');
    const collapseAllBtn = document.getElementById('collapse-all');

    if (expandAllBtn) {
        expandAllBtn.addEventListener('click', () => {
            treeVisualizer.expandAll();
        });
    }

    if (collapseAllBtn) {
        collapseAllBtn.addEventListener('click', () => {
            treeVisualizer.collapseAll();
        });
    }

    // Export CSV button
    const exportCsvBtn = document.getElementById('export-csv');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', () => {
            exportToCSV();
        });
    }
}

function switchView(viewType) {
    console.log('Switching to view:', viewType);

    const viewData = dataLoader.getViewData(viewType);
    if (viewData) {
        treeVisualizer.render(viewData);
    } else {
        console.error('View data not available:', viewType);
    }
}

function switchLayout(layoutType) {
    console.log('Switching to layout:', layoutType);

    treeVisualizer.setLayout(layoutType);

    // Get current view mode
    const viewMode = document.getElementById('view-mode').value;
    const viewData = dataLoader.getViewData(viewMode);

    if (viewData) {
        treeVisualizer.render(viewData);
    } else {
        console.error('View data not available for layout switch');
    }
}

function updateFooter(metadata) {
    if (!metadata) return;

    const vendorsEl = document.getElementById('total-vendors');
    const parsersEl = document.getElementById('total-parsers');
    const updatedEl = document.getElementById('last-updated');

    if (vendorsEl && metadata.total_vendors !== undefined) {
        vendorsEl.textContent = `Vendors: ${metadata.total_vendors}`;
    }

    if (parsersEl && metadata.total_parsers !== undefined) {
        parsersEl.textContent = `Parsers: ${metadata.total_parsers}`;
    }

    if (updatedEl && metadata.scraped_at) {
        const date = new Date(metadata.scraped_at);
        updatedEl.textContent = `Last updated: ${date.toLocaleString()}`;
    }
}

function showLoading() {
    const container = document.getElementById('tree-container');
    if (container) {
        container.innerHTML = `
            <div class="text-center p-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">Loading SC4S parser data...</p>
            </div>
        `;
    }
}

function hideLoading() {
    // Loading message is replaced by tree visualization
}

function showError(error) {
    const container = document.getElementById('tree-container');
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <h4 class="alert-heading">Failed to Load Data</h4>
                <p>${error.message}</p>
                <hr>
                <p class="mb-0">
                    <strong>To generate data, run:</strong><br>
                    <code>python -m src.cli.main scrape</code>
                </p>
            </div>
        `;
    }
}

function exportToCSV() {
    if (!dataLoader || !dataLoader.data) {
        console.error('No data available for export');
        alert('No data available for export. Please load data first.');
        return;
    }

    console.log('Exporting to CSV...');

    try {
        csvExporter.exportToCSV(dataLoader.data);
        console.log('CSV export successful');
    } catch (error) {
        console.error('Failed to export CSV:', error);
        alert('Failed to export CSV: ' + error.message);
    }
}
