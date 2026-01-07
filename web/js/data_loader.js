/**
 * Data Loader - Load and manage SC4S parser data
 */

class DataLoader {
    constructor() {
        this.data = null;
        this.currentView = 'vendor';
    }

    async load(url = '/data/parsed/sc4s_tree.json') {
        try {
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.data = await response.json();
            console.log('Data loaded successfully:', this.data.metadata);

            return this.data;
        } catch (error) {
            console.error('Failed to load data:', error);
            throw error;
        }
    }

    getViewData(viewType = 'vendor') {
        if (!this.data || !this.data.views) {
            return null;
        }

        return this.data.views[viewType];
    }

    getParsersFlat() {
        if (!this.data || !this.data.parsers_flat) {
            return [];
        }

        return this.data.parsers_flat;
    }

    getMetadata() {
        return this.data ? this.data.metadata : null;
    }

    getStats() {
        if (!this.data || !this.data.metadata) {
            return null;
        }

        return {
            vendors: this.data.metadata.total_vendors,
            products: this.data.metadata.total_products,
            parsers: this.data.metadata.total_parsers,
            lastUpdated: this.data.metadata.scraped_at
        };
    }
}
