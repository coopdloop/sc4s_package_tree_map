/**
 * Detail Panel Component
 * Displays detailed information about a selected parser
 */

class DetailPanel {
    constructor(panelId) {
        this.panel = document.getElementById(panelId);
    }

    showParserDetails(parser) {
        const html = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">
                        <i class="bi bi-code-square"></i> ${this.escapeHtml(parser.name)}
                    </h5>
                </div>
                <div class="card-body">
                    ${this.renderParserInfo(parser)}
                    ${this.renderMetadata(parser)}
                    ${this.renderFilters(parser)}
                    ${this.renderApplications(parser)}
                    ${this.renderConditionalRewrites(parser)}
                    ${this.renderNestedParsers(parser)}
                    ${this.renderGitHubLink(parser)}
                </div>
            </div>
        `;

        this.panel.innerHTML = html;
    }

    renderParserInfo(parser) {
        return `
            <div class="mb-3">
                <h6 class="text-muted">Parser Information</h6>
                <table class="table table-sm">
                    <tbody>
                        <tr>
                            <th width="30%">Type:</th>
                            <td><span class="badge bg-info">${parser.parser_type.toUpperCase()}</span></td>
                        </tr>
                        <tr>
                            <th>Vendor:</th>
                            <td>${this.escapeHtml(parser.vendor)}</td>
                        </tr>
                        <tr>
                            <th>Product:</th>
                            <td>${this.escapeHtml(parser.product)}</td>
                        </tr>
                        <tr>
                            <th>File:</th>
                            <td><small><code>${this.escapeHtml(parser.file_path)}</code></small></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
    }

    renderMetadata(parser) {
        if (!parser.metadata || Object.keys(parser.metadata).length === 0) {
            return '';
        }

        let rows = '';
        for (const [key, value] of Object.entries(parser.metadata)) {
            if (value) {
                rows += `
                    <tr>
                        <th width="30%">${this.capitalize(key)}:</th>
                        <td><code>${this.escapeHtml(value)}</code></td>
                    </tr>
                `;
            }
        }

        return `
            <div class="mb-3">
                <h6 class="text-muted">Metadata</h6>
                <table class="table table-sm metadata-table">
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderFilters(parser) {
        if (!parser.applications || parser.applications.length === 0) {
            return '';
        }

        const allFilters = [];
        parser.applications.forEach(app => {
            if (app.filters) {
                allFilters.push(...app.filters);
            }
        });

        if (allFilters.length === 0) {
            return '';
        }

        let filterItems = allFilters.map(filter => {
            const flags = filter.flags && filter.flags.length > 0
                ? `<small class="text-muted">[${filter.flags.join(', ')}]</small>`
                : '';

            return `
                <li class="list-group-item">
                    <strong>${filter.type}:</strong>
                    <code>${this.escapeHtml(filter.pattern)}</code>
                    ${flags}
                    <br>
                    <small class="text-muted">Match type: ${filter.match_type}</small>
                </li>
            `;
        }).join('');

        return `
            <div class="mb-3">
                <h6 class="text-muted">Filter Patterns</h6>
                <ul class="list-group list-group-flush">
                    ${filterItems}
                </ul>
            </div>
        `;
    }

    renderApplications(parser) {
        if (!parser.applications || parser.applications.length === 0) {
            return '';
        }

        let appItems = parser.applications.map(app => {
            return `
                <li class="list-group-item">
                    <strong>${this.escapeHtml(app.name)}</strong>
                    <span class="badge bg-secondary ms-2">${app.type}</span>
                    <br>
                    <small class="text-muted">${app.filters ? app.filters.length : 0} filter(s)</small>
                </li>
            `;
        }).join('');

        return `
            <div class="mb-3">
                <h6 class="text-muted">Applications</h6>
                <ul class="list-group list-group-flush">
                    ${appItems}
                </ul>
            </div>
        `;
    }

    renderConditionalRewrites(parser) {
        if (!parser.conditional_rewrites || parser.conditional_rewrites.length === 0) {
            return '';
        }

        let items = parser.conditional_rewrites.map(cr => {
            const condition = cr.condition
                ? `<code>${this.escapeHtml(cr.condition.pattern)}</code>`
                : '<em>default</em>';

            const metadata = cr.metadata.sourcetype
                ? `→ <code>${this.escapeHtml(cr.metadata.sourcetype)}</code>`
                : '';

            return `
                <li class="list-group-item">
                    <span class="badge bg-warning text-dark">${cr.condition_type}</span>
                    ${condition}
                    ${metadata}
                </li>
            `;
        }).join('');

        return `
            <div class="mb-3">
                <h6 class="text-muted">Conditional Rewrites</h6>
                <ul class="list-group list-group-flush">
                    ${items}
                </ul>
            </div>
        `;
    }

    renderNestedParsers(parser) {
        if (!parser.nested_parsers || parser.nested_parsers.length === 0) {
            return '';
        }

        const badges = parser.nested_parsers.map(np =>
            `<span class="badge bg-secondary me-1">${np}</span>`
        ).join('');

        return `
            <div class="mb-3">
                <h6 class="text-muted">Nested Parsers</h6>
                <div>${badges}</div>
            </div>
        `;
    }

    renderGitHubLink(parser) {
        const baseUrl = 'https://github.com/splunk/splunk-connect-for-syslog/blob/main';
        const url = `${baseUrl}/${parser.file_path}`;

        return `
            <div class="mt-3">
                <a href="${url}" target="_blank" class="btn btn-sm btn-outline-primary">
                    <i class="bi bi-github"></i> View on GitHub
                </a>
            </div>
        `;
    }

    clear() {
        this.panel.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h5>Parser Details</h5>
                </div>
                <div class="card-body">
                    <p class="text-muted">Click on a parser node to view details</p>
                </div>
            </div>
        `;
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

    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
}
