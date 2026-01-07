/**
 * Search Engine using Fuse.js for fuzzy search
 */

class SearchEngine {
    constructor(parsers, treeVisualizer, detailPanel) {
        this.parsers = parsers;
        this.treeVisualizer = treeVisualizer;
        this.detailPanel = detailPanel;
        this.results = [];
        this.autocompleteItems = [];
        this.selectedAutocompleteIndex = -1;

        // Build autocomplete data
        this.buildAutocompleteData();

        // Configure Fuse.js for full search
        this.fuse = new Fuse(parsers, {
            keys: [
                { name: 'name', weight: 0.3 },
                { name: 'vendor', weight: 0.2 },
                { name: 'product', weight: 0.2 },
                { name: 'metadata.sourcetype', weight: 0.15 },
                { name: 'metadata.index', weight: 0.15 }
            ],
            threshold: 0.4,
            includeScore: true,
            minMatchCharLength: 2
        });

        // Configure Fuse.js for autocomplete
        this.autocompleteFuse = new Fuse(this.autocompleteItems, {
            keys: ['value', 'category'],
            threshold: 0.3,
            includeScore: true,
            minMatchCharLength: 1
        });

        this.setupAutocomplete();
    }

    buildAutocompleteData() {
        const vendors = new Set();
        const products = new Set();
        const sourcetypes = new Set();
        const indexes = new Set();

        this.parsers.forEach(parser => {
            if (parser.vendor) vendors.add(parser.vendor);
            if (parser.product) products.add(parser.product);
            if (parser.metadata?.sourcetype) sourcetypes.add(parser.metadata.sourcetype);
            if (parser.metadata?.index) indexes.add(parser.metadata.index);
        });

        // Build autocomplete items with categories
        this.autocompleteItems = [
            ...Array.from(vendors).map(v => ({ value: v, category: 'Vendor', type: 'vendor' })),
            ...Array.from(products).map(p => ({ value: p, category: 'Product', type: 'product' })),
            ...Array.from(sourcetypes).map(s => ({ value: s, category: 'Sourcetype', type: 'sourcetype' })),
            ...Array.from(indexes).map(i => ({ value: i, category: 'Index', type: 'index' }))
        ];
    }

    setupAutocomplete() {
        const searchInput = document.getElementById('search');
        const dropdown = document.getElementById('autocomplete-dropdown');

        if (!searchInput || !dropdown) return;

        // Handle input
        searchInput.addEventListener('input', (e) => {
            this.showAutocomplete(e.target.value);
        });

        // Handle keyboard navigation
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateAutocomplete(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateAutocomplete(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (this.selectedAutocompleteIndex >= 0) {
                    this.selectAutocompleteItem(this.selectedAutocompleteIndex);
                }
            } else if (e.key === 'Escape') {
                this.hideAutocomplete();
            }
        });

        // Handle clicks outside
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
                this.hideAutocomplete();
            }
        });
    }

    search(query) {
        if (!query || query.length < 2) {
            this.results = [];
            this.clearResults();
            this.treeVisualizer.clearHighlights();
            return [];
        }

        // Perform search
        const fuseResults = this.fuse.search(query);
        this.results = fuseResults.map(r => r.item);

        // Display results
        this.displayResults(this.results);

        // Auto-expand tree to show all matching results
        if (this.results.length > 0) {
            this.treeVisualizer.expandToNode(query);
        }

        return this.results;
    }

    displayResults(results) {
        const resultsContainer = document.getElementById('search-results');

        if (!resultsContainer) return;

        // Show results container
        resultsContainer.style.display = 'block';

        if (results.length === 0) {
            resultsContainer.innerHTML = `
                <div class="alert alert-info m-0">
                    No parsers found matching your search.
                </div>
            `;
            return;
        }

        const resultHtml = results.map((parser, index) => `
            <div class="search-result-item p-2 border-bottom" data-index="${index}" style="cursor: pointer;">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${this.escapeHtml(parser.name)}</strong>
                        <br>
                        <small class="text-muted">
                            ${this.escapeHtml(parser.vendor)} / ${this.escapeHtml(parser.product)}
                        </small>
                        ${parser.metadata.sourcetype ? `
                            <br>
                            <small><code>${this.escapeHtml(parser.metadata.sourcetype)}</code></small>
                        ` : ''}
                    </div>
                    <span class="badge bg-${this.getTypeColor(parser.parser_type)}">${parser.parser_type}</span>
                </div>
            </div>
        `).join('');

        resultsContainer.innerHTML = `
            <div class="search-results-header p-2 bg-light border-bottom">
                <small><strong>${results.length}</strong> result${results.length > 1 ? 's' : ''} found</small>
            </div>
            ${resultHtml}
        `;

        // Add click handlers
        resultsContainer.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.selectResult(index);
            });
        });
    }

    selectResult(index) {
        if (index < 0 || index >= this.results.length) return;

        const parser = this.results[index];

        // Show details
        this.detailPanel.showParserDetails(parser);

        // Expand tree to show this specific parser
        this.treeVisualizer.expandToNode(parser.name);

        // Highlight selected result
        document.querySelectorAll('.search-result-item').forEach((item, i) => {
            if (i === index) {
                item.classList.add('bg-primary', 'text-white');
            } else {
                item.classList.remove('bg-primary', 'text-white');
            }
        });
    }

    clearResults() {
        const resultsContainer = document.getElementById('search-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
            resultsContainer.style.display = 'none';
        }
    }

    getTypeColor(type) {
        const colors = {
            'syslog': 'primary',
            'json': 'success',
            'cef': 'warning',
            'leef': 'info',
            'raw': 'secondary'
        };
        return colors[type] || 'secondary';
    }

    escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.toString().replace(/[&<>"']/g, m => map[m]);
    }

    showAutocomplete(query) {
        const dropdown = document.getElementById('autocomplete-dropdown');
        if (!dropdown) return;

        if (!query || query.length < 1) {
            this.hideAutocomplete();
            return;
        }

        // Search autocomplete items
        const results = this.autocompleteFuse.search(query);
        const items = results.map(r => r.item).slice(0, 10); // Limit to 10 results

        if (items.length === 0) {
            this.hideAutocomplete();
            return;
        }

        // Group by category
        const grouped = {};
        items.forEach(item => {
            if (!grouped[item.category]) {
                grouped[item.category] = [];
            }
            grouped[item.category].push(item);
        });

        // Build HTML
        let html = '';
        let itemIndex = 0;
        Object.keys(grouped).forEach(category => {
            html += `<div class="autocomplete-category">${category}</div>`;
            grouped[category].forEach(item => {
                const highlighted = this.highlightMatch(item.value, query);
                html += `
                    <div class="autocomplete-item" data-index="${itemIndex}" data-value="${this.escapeHtml(item.value)}">
                        <div class="item-name">${highlighted}</div>
                        <div class="item-details">${item.type}</div>
                    </div>
                `;
                itemIndex++;
            });
        });

        dropdown.innerHTML = html;
        dropdown.classList.add('show');

        // Add click handlers
        dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.selectAutocompleteItem(index);
            });

            item.addEventListener('mouseenter', (e) => {
                this.selectedAutocompleteIndex = parseInt(e.currentTarget.dataset.index);
                this.updateAutocompleteSelection();
            });
        });

        this.selectedAutocompleteIndex = -1;
    }

    hideAutocomplete() {
        const dropdown = document.getElementById('autocomplete-dropdown');
        if (dropdown) {
            dropdown.classList.remove('show');
            dropdown.innerHTML = '';
        }
        this.selectedAutocompleteIndex = -1;
    }

    navigateAutocomplete(direction) {
        const dropdown = document.getElementById('autocomplete-dropdown');
        if (!dropdown || !dropdown.classList.contains('show')) return;

        const items = dropdown.querySelectorAll('.autocomplete-item');
        if (items.length === 0) return;

        this.selectedAutocompleteIndex += direction;

        if (this.selectedAutocompleteIndex < 0) {
            this.selectedAutocompleteIndex = items.length - 1;
        } else if (this.selectedAutocompleteIndex >= items.length) {
            this.selectedAutocompleteIndex = 0;
        }

        this.updateAutocompleteSelection();
    }

    updateAutocompleteSelection() {
        const dropdown = document.getElementById('autocomplete-dropdown');
        if (!dropdown) return;

        dropdown.querySelectorAll('.autocomplete-item').forEach((item, index) => {
            if (index === this.selectedAutocompleteIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    selectAutocompleteItem(index) {
        const dropdown = document.getElementById('autocomplete-dropdown');
        if (!dropdown) return;

        const items = dropdown.querySelectorAll('.autocomplete-item');
        if (index < 0 || index >= items.length) return;

        const selectedValue = items[index].dataset.value;
        const searchInput = document.getElementById('search');

        if (searchInput) {
            searchInput.value = selectedValue;
            searchInput.focus();
        }

        this.hideAutocomplete();

        // Trigger search with selected value
        this.search(selectedValue);
    }

    highlightMatch(text, query) {
        if (!text || !query) return this.escapeHtml(text);

        const escapedText = this.escapeHtml(text);
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');

        return escapedText.replace(regex, '<span class="match-highlight">$1</span>');
    }
}
