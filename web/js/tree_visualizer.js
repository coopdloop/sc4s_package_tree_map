/**
 * D3.js Tree Visualizer for SC4S Parser Hierarchy
 */

class TreeVisualizer {
    constructor(containerId, detailPanel) {
        this.container = d3.select(`#${containerId}`);
        this.detailPanel = detailPanel;

        // Dimensions - make it bigger for better spacing
        this.margin = { top: 20, right: 120, bottom: 30, left: 120 };
        this.width = 2000 - this.margin.left - this.margin.right;
        this.height = 1400 - this.margin.top - this.margin.bottom;

        // Clear any existing content (like loading spinner)
        this.container.html('');

        // Create SVG
        this.svg = this.container
            .append('svg')
            .attr('width', '100%')
            .attr('height', this.height + this.margin.top + this.margin.bottom);

        // Create zoom group
        this.g = this.svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Create tree layout
        this.treemap = d3.tree().size([this.height, this.width]);

        // State
        this.root = null;
        this.i = 0;
        this.duration = 750;
        this.currentLayout = 'tree'; // 'tree', 'radial', or 'force'

        // Setup zoom
        this.setupZoom();
    }

    setupZoom() {
        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });

        this.svg.call(zoom);
    }

    setLayout(layout) {
        this.currentLayout = layout;
    }

    render(data) {
        // Store current data for re-rendering
        this.currentData = data;

        // Clear existing
        this.g.selectAll('*').remove();

        // Reset transform for tree layout
        if (this.currentLayout === 'tree') {
            this.g.attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        }

        // Assigns parent, children, height, depth
        this.root = d3.hierarchy(data, d => d.children);
        this.root.x0 = this.height / 2;
        this.root.y0 = 0;

        // Collapse all children initially except first level
        if (this.root.children) {
            this.root.children.forEach(child => {
                if (child.children) {
                    this.collapse(child);
                }
            });
        }

        // Render based on layout mode
        if (this.currentLayout === 'radial') {
            this.renderRadial(this.root);
        } else if (this.currentLayout === 'force') {
            this.renderForce(data);
        } else {
            this.update(this.root);
        }
    }

    collapse(d) {
        if (d.children) {
            d._children = d.children;
            d._children.forEach(child => this.collapse(child));
            d.children = null;
        }
    }

    update(source) {
        // Assigns the x and y position for the nodes
        const treeData = this.treemap(this.root);

        // Compute the new tree layout
        const nodes = treeData.descendants();
        const links = treeData.descendants().slice(1);

        // Normalize for fixed-depth with better spacing
        nodes.forEach(d => { d.y = d.depth * 180 });

        // ****************** Nodes section ***************************

        // Update the nodes
        const node = this.g.selectAll('g.node')
            .data(nodes, d => d.id || (d.id = ++this.i));

        // Enter any new nodes at the parent's previous position
        const nodeEnter = node.enter().append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${source.y0},${source.x0})`)
            .on('click', (event, d) => this.click(event, d));

        // Add Circle for the nodes
        nodeEnter.append('circle')
            .attr('class', 'node-circle')
            .attr('r', 1e-6)
            .style('fill', d => this.getNodeColor(d))
            .style('stroke', d => this.getNodeStroke(d))
            .style('stroke-width', '2px')
            .style('cursor', 'pointer');

        // Add labels for the nodes
        nodeEnter.append('text')
            .attr('dy', '.35em')
            .attr('x', d => d.children || d._children ? -13 : 13)
            .attr('text-anchor', d => d.children || d._children ? 'end' : 'start')
            .text(d => d.data.name)
            .style('font-size', '12px')
            .style('font-family', 'monospace')
            .style('fill-opacity', 1e-6);

        // UPDATE
        const nodeUpdate = nodeEnter.merge(node);

        // Transition to the proper position for the node
        nodeUpdate.transition()
            .duration(this.duration)
            .attr('transform', d => `translate(${d.y},${d.x})`);

        // Update the node attributes and style
        nodeUpdate.select('circle.node-circle')
            .attr('r', d => this.getNodeSize(d))
            .style('fill', d => this.getNodeColor(d))
            .attr('cursor', 'pointer');

        nodeUpdate.select('text')
            .style('fill-opacity', 1);

        // Remove any exiting nodes
        const nodeExit = node.exit().transition()
            .duration(this.duration)
            .attr('transform', d => `translate(${source.y},${source.x})`)
            .remove();

        // On exit reduce the node circles size to 0
        nodeExit.select('circle')
            .attr('r', 1e-6);

        // On exit reduce the opacity of text labels
        nodeExit.select('text')
            .style('fill-opacity', 1e-6);

        // ****************** links section ***************************

        // Update the links
        const link = this.g.selectAll('path.link')
            .data(links, d => d.id);

        // Enter any new links at the parent's previous position
        const linkEnter = link.enter().insert('path', 'g')
            .attr('class', 'link')
            .attr('d', d => {
                const o = { x: source.x0, y: source.y0 };
                return this.diagonal(o, o);
            })
            .style('fill', 'none')
            .style('stroke', '#ccc')
            .style('stroke-width', '2px');

        // UPDATE
        const linkUpdate = linkEnter.merge(link);

        // Transition back to the parent element position
        linkUpdate.transition()
            .duration(this.duration)
            .attr('d', d => this.diagonal(d, d.parent));

        // Remove any exiting links
        link.exit().transition()
            .duration(this.duration)
            .attr('d', d => {
                const o = { x: source.x, y: source.y };
                return this.diagonal(o, o);
            })
            .remove();

        // Store the old positions for transition
        nodes.forEach(d => {
            d.x0 = d.x;
            d.y0 = d.y;
        });
    }

    diagonal(s, d) {
        // Creates a curved (diagonal) path from parent to the child nodes
        return `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`;
    }

    click(event, d) {
        if (d.data.type === 'parser') {
            // Show parser details
            this.detailPanel.showParserDetails(d.data);
        } else {
            // Toggle children
            if (d.children) {
                d._children = d.children;
                d.children = null;
            } else {
                d.children = d._children;
                d._children = null;
            }
            this.update(d);
        }
    }

    getNodeColor(d) {
        if (d._children) {
            // Has collapsed children
            return this.getNodeTypeColor(d.data.type);
        } else if (d.children) {
            // Has expanded children
            return '#fff';
        } else {
            // Leaf node
            return '#fff';
        }
    }

    getNodeStroke(d) {
        return this.getNodeTypeColor(d.data.type);
    }

    getNodeTypeColor(type) {
        const colors = {
            'root': '#333',
            'vendor': '#4285F4',
            'product': '#0F9D58',
            'parser': '#DB4437',
            'parser_type': '#F4B400',
            'index': '#AB47BC'
        };
        return colors[type] || '#999';
    }

    getNodeSize(d) {
        if (d.data.type === 'root') return 8;
        if (d.data.type === 'parser') return 5;
        return 6;
    }

    highlightNode(nodeId) {
        this.g.selectAll('circle')
            .style('stroke-width', d =>
                d.data.name === nodeId ? '4px' : '2px'
            )
            .style('filter', d =>
                d.data.name === nodeId ? 'drop-shadow(0 0 8px rgba(66, 133, 244, 0.8))' : 'none'
            );
    }

    clearHighlights() {
        this.g.selectAll('circle')
            .style('stroke-width', '2px')
            .style('filter', 'none');
    }

    expandToNode(searchName) {
        if (!this.root) return;

        // Find all nodes matching the search term
        const matchingNodes = [];
        this.findMatchingNodes(this.root, searchName.toLowerCase(), matchingNodes);

        if (matchingNodes.length === 0) {
            console.log('No matching nodes found for:', searchName);
            return;
        }

        // Expand path to each matching node
        matchingNodes.forEach(node => {
            this.expandPathToNode(node);
        });

        // Re-render the tree
        this.renderCurrentLayout();

        // Highlight the matching nodes
        this.highlightMultipleNodes(matchingNodes.map(n => n.data.name));
    }

    findMatchingNodes(node, searchTerm, results) {
        // Check if this node matches
        const nodeName = node.data.name ? node.data.name.toLowerCase() : '';
        const vendor = node.data.vendor ? node.data.vendor.toLowerCase() : '';
        const product = node.data.product ? node.data.product.toLowerCase() : '';

        if (nodeName.includes(searchTerm) ||
            vendor.includes(searchTerm) ||
            product.includes(searchTerm)) {
            results.push(node);
        }

        // Check children
        const children = node.children || node._children;
        if (children) {
            children.forEach(child => {
                this.findMatchingNodes(child, searchTerm, results);
            });
        }
    }

    expandPathToNode(node) {
        // Expand all parents up to root
        let current = node.parent;
        while (current) {
            if (current._children) {
                current.children = current._children;
                current._children = null;
            }
            current = current.parent;
        }
    }

    highlightMultipleNodes(nodeNames) {
        this.g.selectAll('circle')
            .style('stroke-width', d =>
                nodeNames.includes(d.data.name) ? '4px' : '2px'
            )
            .style('filter', d =>
                nodeNames.includes(d.data.name) ? 'drop-shadow(0 0 8px rgba(219, 68, 55, 0.8))' : 'none'
            );
    }

    collapseAll() {
        if (this.root && this.root.children) {
            this.root.children.forEach(child => this.collapse(child));
            // Re-render using current layout mode
            this.renderCurrentLayout();
        }
    }

    expandAll() {
        if (this.root) {
            this.expandRecursive(this.root);
            // Re-render using current layout mode
            this.renderCurrentLayout();
        }
    }

    renderCurrentLayout() {
        // Get the original data to re-render
        if (!this.currentData) return;

        if (this.currentLayout === 'radial') {
            this.g.selectAll('*').remove();
            this.renderRadial(this.root);
        } else if (this.currentLayout === 'force') {
            this.g.selectAll('*').remove();
            this.renderForce(this.currentData);
        } else {
            this.update(this.root);
        }
    }

    expandRecursive(d) {
        if (d._children) {
            d.children = d._children;
            d._children = null;
        }
        if (d.children) {
            d.children.forEach(child => this.expandRecursive(child));
        }
    }

    renderRadial(source) {
        // Create radial tree layout
        const radius = Math.min(this.width, this.height) / 2;
        const tree = d3.tree()
            .size([2 * Math.PI, radius])
            .separation((a, b) => (a.parent == b.parent ? 1 : 2) / a.depth);

        const treeData = tree(this.root);
        const nodes = treeData.descendants();
        const links = treeData.links();

        // Transform to center
        this.g.attr('transform', `translate(${this.width / 2},${this.height / 2})`);

        // Links
        this.g.selectAll('path.link')
            .data(links)
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('d', d3.linkRadial()
                .angle(d => d.x)
                .radius(d => d.y))
            .style('fill', 'none')
            .style('stroke', '#ccc')
            .style('stroke-width', '2px');

        // Nodes
        const node = this.g.selectAll('g.node')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', 'node')
            .attr('transform', d => `rotate(${d.x * 180 / Math.PI - 90}) translate(${d.y},0)`)
            .on('click', (event, d) => this.click(event, d));

        node.append('circle')
            .attr('r', d => this.getNodeSize(d))
            .style('fill', d => this.getNodeColor(d))
            .style('stroke', d => this.getNodeStroke(d))
            .style('stroke-width', '2px')
            .style('cursor', 'pointer');

        node.append('text')
            .attr('dy', '0.31em')
            .attr('x', d => d.x < Math.PI === !d.children ? 6 : -6)
            .attr('text-anchor', d => d.x < Math.PI === !d.children ? 'start' : 'end')
            .attr('transform', d => d.x >= Math.PI ? 'rotate(180)' : null)
            .text(d => d.data.name)
            .style('font-size', '10px')
            .style('font-family', 'monospace');
    }

    renderForce(data) {
        // Convert hierarchical data to flat nodes and links
        const root = d3.hierarchy(data);
        const nodes = root.descendants();
        const links = root.links();

        // Create force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).distance(100).strength(1))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(30));

        // Create links
        const link = this.g.selectAll('line.link')
            .data(links)
            .enter()
            .append('line')
            .attr('class', 'link')
            .style('stroke', '#ccc')
            .style('stroke-width', '2px');

        // Create nodes
        const node = this.g.selectAll('g.node')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', (event, d) => {
                    if (!event.active) simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                }))
            .on('click', (event, d) => {
                event.stopPropagation();
                this.detailPanel.showParserDetails(d.data);
            });

        node.append('circle')
            .attr('r', d => this.getNodeSize(d) * 2)
            .style('fill', d => this.getNodeColor(d))
            .style('stroke', d => this.getNodeStroke(d))
            .style('stroke-width', '2px')
            .style('cursor', 'pointer');

        node.append('text')
            .attr('dy', '0.31em')
            .attr('x', 12)
            .text(d => d.data.name)
            .style('font-size', '10px')
            .style('font-family', 'monospace')
            .style('pointer-events', 'none');

        // Update positions on simulation tick
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }
}
