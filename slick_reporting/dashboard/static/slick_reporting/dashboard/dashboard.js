/* Slick Reporting Dashboard — configurator logic */
(function () {
    "use strict";

    function escapeHtml(str) {
        var d = document.createElement("div");
        d.textContent = str || "";
        return d.innerHTML;
    }

    function buildPlaceholderHTML(title) {
        return (
            '<div class="h-100 d-flex flex-column">' +
            '<div class="d-flex align-items-center px-2 py-1 bg-light border-bottom widget-placeholder-header">' +
            '<i class="fas fa-grip-vertical text-muted me-2"></i>' +
            '<span class="fw-semibold small flex-grow-1 text-truncate">' + escapeHtml(title) + "</span>" +
            '<button type="button" class="btn btn-sm btn-link text-danger p-0 ms-1 remove-widget-btn" title="Remove">' +
            '<i class="fas fa-times"></i></button>' +
            "</div>" +
            '<div class="flex-grow-1 d-flex align-items-center justify-content-center text-muted">' +
            '<div class="text-center"><i class="fas fa-chart-bar fa-2x mb-1 opacity-25"></i>' +
            '<div class="small">Chart / Table</div></div></div>' +
            "</div>"
        );
    }

    function bindRemoveButton(grid, itemEl) {
        var btn = itemEl.querySelector(".remove-widget-btn");
        if (!btn || btn._srBound) return;
        btn._srBound = true;
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            grid.removeWidget(itemEl);
        });
    }

    var SlickDashboard = {
        initConfigurator: function (opts) {
            var saveUrl = opts.saveUrl;
            var viewUrl = opts.viewUrl;
            var csrfToken = opts.csrfToken;
            var pendingDragData = null;

            var grid = GridStack.init(
                {
                    column: 12,
                    cellHeight: 80,
                    resizable: { handles: "se" },
                    float: false,
                    animate: true,
                    acceptWidgets: true,
                },
                opts.gridEl
            );

            // Bind remove buttons on widgets already in the grid
            document.querySelectorAll(opts.gridEl + " .grid-stack-item").forEach(function (el) {
                bindRemoveButton(grid, el);
            });

            // Make sidebar items draggable into the grid
            GridStack.setupDragIn(".sidebar-report-item", {
                appendTo: "body",
                helper: "clone",
            });

            // Track what's being dragged via mousedown (reliable across drag implementations)
            document.querySelectorAll(".sidebar-report-item").forEach(function (el) {
                el.addEventListener("mousedown", function () {
                    pendingDragData = {
                        reportUrlName: el.dataset.reportUrlName,
                        reportTitle: el.dataset.reportTitle,
                    };
                });
            });

            // Handle newly added items (drag-drop from sidebar or click-to-add)
            grid.on("added", function (event, items) {
                items.forEach(function (item) {
                    var el = item.el;
                    if (pendingDragData) {
                        el.dataset.reportUrlName = pendingDragData.reportUrlName;
                        el.dataset.reportTitle = pendingDragData.reportTitle;
                        el.dataset.displayChart = "true";
                        el.dataset.displayTable = "false";
                        var content = el.querySelector(".grid-stack-item-content");
                        if (content) {
                            content.innerHTML = buildPlaceholderHTML(pendingDragData.reportTitle);
                        }
                        pendingDragData = null;
                    }
                    bindRemoveButton(grid, el);
                });
            });

            // Click-to-add buttons in the sidebar (alternative to drag)
            document.querySelectorAll(".add-report-btn").forEach(function (btn) {
                btn.addEventListener("click", function (e) {
                    e.stopPropagation();
                    pendingDragData = {
                        reportUrlName: btn.dataset.reportUrlName,
                        reportTitle: btn.dataset.reportTitle,
                    };
                    grid.addWidget({ w: 6, h: 4 });
                });
            });

            // Save dashboard layout
            var saveBtn = document.getElementById("save-dashboard-btn");
            if (!saveBtn) return;

            saveBtn.addEventListener("click", function () {
                var widgets = [];
                grid.getGridItems().forEach(function (el) {
                    var node = el.gridstackNode;
                    if (!node) return;
                    var urlName = el.dataset.reportUrlName;
                    if (!urlName) return;
                    widgets.push({
                        report_url_name: urlName,
                        title: el.dataset.reportTitle || "",
                        gs_x: node.x,
                        gs_y: node.y,
                        gs_w: node.w,
                        gs_h: node.h,
                        display_chart: el.dataset.displayChart !== "false",
                        display_table: el.dataset.displayTable === "true",
                        chart_id: parseInt(el.dataset.chartId || "0", 10),
                    });
                });

                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving…';

                fetch(saveUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ widgets: widgets }),
                })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data.status === "ok") {
                            window.location.href = viewUrl;
                        } else {
                            alert("Save failed: " + (data.message || "Unknown error"));
                            saveBtn.disabled = false;
                            saveBtn.innerHTML = '<i class="fas fa-save me-1"></i>Save';
                        }
                    })
                    .catch(function (err) {
                        alert("Network error: " + err);
                        saveBtn.disabled = false;
                        saveBtn.innerHTML = '<i class="fas fa-save me-1"></i>Save';
                    });
            });
        },
    };

    window.SlickDashboard = SlickDashboard;
})();
