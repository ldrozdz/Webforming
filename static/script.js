const style = {
    graph: {
        circle: "cursor: pointer; stroke: #3182bd; fill: #fd8d3c;",
        label: "font: 10px sans-serif; pointer-events: none;",
        link: "fill: none; stroke: #b9d4e1; stroke-width: 1.5px;"
    },
    tree: {
        node: "cursor: pointer",
        circle: "fill: #fff; stroke: steelblue; stroke-width: 1.5px;",
        label: "font-size:10px; font-family:sans-serif;",
        link: "fill: none; stroke: #ccc; stroke-width: 1.5px;"
    }
}

function submit_download_form(id) {
    // Get the d3js SVG element
    var plot = $('#plot');
    var svg = plot.children("svg")[0];
    // Extract the data as SVG text string
    var svg_xml = (new XMLSerializer).serializeToString(svg);

    // Submit the <FORM> to the server.
    // The result will be an attachment file to download.
    var form = $('#downloadform')[0];
    form['filename'].value = id;
    form['data'].value = svg_xml;
    form.submit();
}

//TODO: for node radius, play with PageRank
function graph(data_file) {

    var width = Math.max($(window).width(), $(document).width(), 1280);
    var height = Math.max($(window).height(), $(document).height(), 1024);

    var force = d3.layout.force()
        .size([width, height])
        .linkDistance(30)
        .friction(0.9)
        .charge(-200);

    var zoom = d3.behavior.zoom()
        .scaleExtent([-10, 10])
        .on("zoom", function () {
            svg.attr("transform", "translate(" + d3.event.translate.join(",") + ")scale(" + d3.event.scale + ")");
        });

    var svg = d3.select("#plot")
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .call(zoom)
        .append("g");

    d3.json(data_file, function (error, graph) {
        var nodes = graph.nodes.slice(),
            links = [],
            bilinks = [];

        graph.links.forEach(function (link) {
            var s = nodes[link.source],
                t = nodes[link.target],
                i = {}; // intermediate node
            nodes.push(i);
            links.push({source: s, target: i}, {source: i, target: t});
            bilinks.push([s, i, t]);
        });

        force.nodes(nodes).links(links).start();

        var drag = d3.behavior.drag()
            .origin(function (d) {
                return d;
            })
            .on("dragstart", function (d, i) {
                force.stop();
                d3.event.sourceEvent.stopPropagation();
            })
            .on("drag", function (d, i) {
                d.px += d3.event.dx;
                d.py += d3.event.dy;
                d.x += d3.event.dx;
                d.y += d3.event.dy;
                tick();
            })
            .on("dragend", function (d, i) {
                d.fixed = true;
//                tick();
                force.resume();
            });

        var link = svg.selectAll(".link")
            .data(bilinks)
            .enter().append("path")
            .attr("style", style.graph.link)
            .attr("class", "link");

        var node = svg.selectAll(".node")
            .data(graph.nodes)
            .enter().append("g")
            .attr("class", "node")
            .call(drag);

        node.append("circle")
            .attr("style", style.graph.circle)
            .attr("stroke-width", function (d) {
                return Math.max((Math.log(d.outdegree) * 1.5), 1.5);
            })
            .attr("r", function (d) {
                return Math.max((Math.log(d.indegree) * 5), 5);
            });

        node.append("text")
            .attr("dx", 12)
            .attr("dy", ".35em")
            .attr("style", style.graph.label)
            .attr("class", "label")
            .text(function (d) {
                return d.name;
            });

        force.on("tick", tick);

        function tick() {
            link.attr("d", function (d) {
                return "M" + d[0].x + "," + d[0].y
                    + "S" + d[1].x + "," + d[1].y
                    + " " + d[2].x + "," + d[2].y;
            });

            node.attr("transform", function (d) {
                return "translate(" + d.x + "," + d.y + ")";
            });
        };

    });
};

//Adapted from http://bl.ocks.org/robschmuecker/7880033
function tree(data_file) {
    treeJSON = d3.json(data_file, function (error, treeData) {

        // Calculate total nodes, max label length
        var totalNodes = 0;
        var maxLabelLength = 0;
        // Misc. variables
        var i = 0;
        var duration = 750;
        var root;

        // size of the diagram
        var viewerWidth = Math.max($(window).width(), $(document).width(), 1280);
        var viewerHeight = Math.max($(window).height(), $(document).height(), 1024);

        var tree = d3.layout.tree()
            .size([viewerHeight, viewerWidth]);

        // define a d3 diagonal projection for use by the node paths later on.
        var diagonal = d3.svg.diagonal()
            .projection(function (d) {
                return [d.x, d.y];
            });

        // A recursive helper function for performing some setup by walking through all nodes

        function visit(parent, visitFn, childrenFn) {
            if (!parent) return;

            visitFn(parent);

            var children = childrenFn(parent);
            if (children) {
                var count = children.length;
                for (var i = 0; i < count; i++) {
                    visit(children[i], visitFn, childrenFn);
                }
            }
        }

        // Call visit function to establish maxLabelLength
        visit(treeData, function (d) {
            totalNodes++;
            maxLabelLength = Math.max(d.name.length, maxLabelLength);

        }, function (d) {
            return d.children && d.children.length > 0 ? d.children : null;
        });


        // sort the tree according to the node names

        function sortTree() {
            tree.sort(function (a, b) {
                return b.name.toLowerCase() < a.name.toLowerCase() ? 1 : -1;
            });
        }

        // Sort the tree initially incase the JSON isn't in a sorted order.
        sortTree();

        // Define the zoom function for the zoomable tree
        function zoom() {
            svgGroup.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
        }

        // define the zoomListener which calls the zoom function on the "zoom" event constrained within the scaleExtents
        var zoomListener = d3.behavior.zoom().scaleExtent([0.1, 3]).on("zoom", zoom);

        // define the baseSvg, attaching a class for styling and the zoomListener
        var baseSvg = d3.select("#plot").append("svg")
            .attr("width", viewerWidth)
            .attr("height", viewerHeight)
            .attr("class", "overlay")
            .call(zoomListener);

        // Helper functions for collapsing and expanding nodes.
        function collapse(d) {
            if (d.children) {
                d._children = d.children;
                d._children.forEach(collapse);
                d.children = null;
            }
        }

        function expand(d) {
            if (d._children) {
                d.children = d._children;
                d.children.forEach(expand);
                d._children = null;
            }
        }

        // Toggle children function
        function toggleChildren(d) {
            if (d.children) {
                d._children = d.children;
                d.children = null;
            } else if (d._children) {
                d.children = d._children;
                d._children = null;
            }
            return d;
        }

        // Toggle children on click.
        function click(d) {
            if (d3.event.defaultPrevented) return; // click suppressed
            d = toggleChildren(d);
            update(d);
        }

        function update(source) {
            // Compute the new height, function counts total children of root node and sets tree height accordingly.
            // This prevents the layout looking squashed when new nodes are made visible or looking sparse when nodes are removed
            // This makes the layout more consistent.
            var levelWidth = [1];
            var childCount = function (level, n) {

                if (n.children && n.children.length > 0) {
                    if (levelWidth.length <= level + 1) levelWidth.push(0);

                    levelWidth[level + 1] += n.children.length;
                    n.children.forEach(function (d) {
                        childCount(level + 1, d);
                    });
                }
            };
            childCount(0, root);
            var newHeight = d3.max(levelWidth) * 25; // 25 pixels per line
            tree = tree.size([newHeight, viewerWidth]);

            // Compute the new tree layout.
            var nodes = tree.nodes(root).reverse(),
                links = tree.links(nodes);

            // Set widths between levels based on maxLabelLength.
            nodes.forEach(function (d) {
                d.y = (d.depth * (maxLabelLength * 10)); //maxLabelLength * 10px
                // alternatively to keep a fixed scale one can set a fixed depth per level
                // Normalize for fixed-depth by commenting out below line
                // d.y = (d.depth * 500); //500px per level.
            });

            // Update the nodes…
            node = svgGroup.selectAll("g.node")
                .data(nodes, function (d) {
                    return d.id || (d.id = ++i);
                });

            // Enter any new nodes at the parent's previous position.
            var nodeEnter = node.enter().append("g")
                .attr("class", "node")
                .attr("style", style.tree.node)
                .attr("transform", function (d) {
                    return "translate(" + source.x0 + "," + source.y0 + ")";
                })
                .on('click', click);

            nodeEnter.append("circle")
                .attr('class', 'nodeCircle')
                .attr("style", style.tree.circle)
                .attr("r", 0)
                .style("fill", function (d) {
                    return d._children ? "lightsteelblue" : "#fff";
                });

            nodeEnter.append("text")
                .attr("x", function (d) {
                    return d.children || d._children ? -10 : 10;
                })
                .attr("dy", ".35em")
                .attr('class', 'nodeText')
                .attr("style", style.tree.label)
                .attr("text-anchor", function (d) {
                    return d.children || d._children ? "end" : "start";
                })
                .text(function (d) {
                    return d.name;
                })
                .style("fill-opacity", 0)
                .attr("transform", "rotate(270,0,0)");

            nodeEnter.append("title")
                .text(function (d) {
                    return d.content;
                });

            // Update the text to reflect whether node has children or not.
            node.select('text')
                .attr("x", function (d) {
                    return d.children || d._children ? -10 : 10;
                })
                .attr("text-anchor", function (d) {
                    return d.children || d._children ? "end" : "start";
                })
                .text(function (d) {
                    return d.name;
                });

            // Change the circle fill depending on whether it has children and is collapsed
            node.select("circle.nodeCircle")
                .attr("r", 4.5)
                .style("fill", function (d) {
                    return d._children ? "lightsteelblue" : "#fff";
                });

            // Transition nodes to their new position.
            var nodeUpdate = node.transition()
                .duration(duration)
                .attr("transform", function (d) {
                    return "translate(" + d.x + "," + d.y + ")";
                });

            // Fade the text in
            nodeUpdate.select("text")
                .style("fill-opacity", 1);

            // Transition exiting nodes to the parent's new position.
            var nodeExit = node.exit().transition()
                .duration(duration)
                .attr("transform", function (d) {
                    return "translate(" + source.x + "," + source.y + ")";
                })
                .remove();

            nodeExit.select("circle")
                .attr("r", 0);

            nodeExit.select("text")
                .style("fill-opacity", 0);

            // Update the links…
            var link = svgGroup.selectAll("path.link")
                .data(links, function (d) {
                    return d.target.id;
                });

            // Enter any new links at the parent's previous position.
            link.enter().insert("path", "g")
                .attr("class", "link")
                .attr("style", style.tree.link)
                .attr("d", function (d) {
                    var o = {
                        x: source.x0,
                        y: source.y0
                    };
                    return diagonal({
                        source: o,
                        target: o
                    });
                });

            // Transition links to their new position.
            link.transition()
                .duration(duration)
                .attr("d", diagonal);

            // Transition exiting nodes to the parent's new position.
            link.exit().transition()
                .duration(duration)
                .attr("d", function (d) {
                    var o = {
                        x: source.x,
                        y: source.y
                    };
                    return diagonal({
                        source: o,
                        target: o
                    });
                })
                .remove();

            // Stash the old positions for transition.
            nodes.forEach(function (d) {
                d.x0 = d.x;
                d.y0 = d.y;
            });
        }

        // Append a group which holds all nodes and which the zoom Listener can act upon.
        var svgGroup = baseSvg.append("g")
            .attr("transform", "translate(" + -(viewerWidth / 2) + ", 10)");

        // Define the root
        root = treeData;
        root.x0 = -(viewerWidth / 2);
        root.y0 = 10;

        zoomListener.translate([-(viewerWidth / 2), 10]);
        // Layout the tree initially and center on the root node.
        update(root);
    });
};

//adapted from http://codepen.io/toadums/details/wjovC
function radial(data_file) {
    d3.json(data_file, function (error, items) {
        var diagonal,
            diameter,
            height,
            items,
            link,
            links,
            node,
            nodes,
            rad,
            svg,
            transformNodes,
            tree,
            width,
            zoom;
        _this = this;

        zoom = function (d) {
            var ev;
            ev = d3.event;
            rad.domain([0, 1 / ev.scale]);
            transformNodes();
            svg.selectAll(".link").attr("d", diagonal);
            return svg.attr("transform", "translate(" + ev.translate + ")");
        };

        var viewerWidth = Math.max($(window).width(), $(document).width(), 1280);
        var viewerHeight = Math.max($(window).height(), $(document).height(), 1024);

        width = height = diameter = 900;

        rad = d3.scale.linear()
            .domain([0, 1])
            .range([0, diameter / 2]);

        tree = d3.layout.tree()
            .size([360, 1])
            .separation(function (a, b) {
                return (a.parent === b.parent ? 1 : 2) / a.depth;
            });

        diagonal = d3.svg.diagonal.radial()
            .projection(function (d) {
                return [rad(d.y), d.x / 180 * Math.PI];
            });

        svg = d3.select($("#plot").get(0))
            .append("svg")
            .attr("width", viewerWidth)
            .attr("height", viewerHeight)
            .call(d3.behavior.zoom()
                .translate([viewerWidth / 2, viewerHeight / 2])
                .scaleExtent([-10, 10]).on("zoom", zoom))
            .append("g")
            .attr("transform", "translate(" + (viewerWidth / 2) + ", " + (viewerHeight / 2) + ")");

        nodes = tree.nodes(items);

        links = tree.links(nodes);

        link = svg.selectAll(".link")
            .data(links)
            .enter()
            .append("path")
            .attr("class", "link")
            .attr("style", style.tree.link)
            .attr("d", diagonal);

        node = svg.selectAll(".node")
            .data(nodes)
            .enter()
            .append("g")
            .attr("class", "node")
            .attr("style", style.tree.node);

        transformNodes = function () {
            return node.attr("transform", function (d) {
                return "rotate(" + (d.x - 90) + ") translate(" + (rad(d.y)) + ")";
            });
        };

        transformNodes();

        node.append("circle")
            .attr("r", 4.5)
            .attr("style", style.tree.circle);

        node.append("text")
            .attr("dy", ".31em")
            .attr("style", style.tree.label)
            .attr("text-anchor",function (d) {
                if (d.x < 180) {
                    return "start";
                }
                else {
                    return "end";
                }
            }).attr("transform",function (d) {
                if (d.x < 180) {
                    return "translate(8)";
                }
                else {
                    return "rotate(180)translate(-8)";
                }
            }).text(function (d) {
                return d.name;
            });

        node.append("title")
            .text(function (d) {
                return d.content;
            });

    });
}