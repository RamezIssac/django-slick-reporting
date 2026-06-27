/* Slick Reporting Dashboard — form-based widget builder & configurator */
(function () {
    "use strict";

    function escapeHtml(str) {
        var d = document.createElement("div");
        d.textContent = str == null ? "" : str;
        return d.innerHTML;
    }

    var SlickDashboard = {
        initConfigurator: function (opts) {
            var $ = window.jQuery;
            var csrfToken = opts.csrfToken;

            // ---- state: ordered placements on this dashboard ----
            var placements = [];
            var previewSeq = 0; // unique ids so slick's per-element chart cache never collides on re-render
            try {
                var raw = document.getElementById("dashboard-initial-data");
                if (raw) placements = JSON.parse(raw.textContent) || [];
            } catch (e) {
                placements = [];
            }

            // Minimal Bootstrap-5 modal controller that does NOT rely on a global
            // `bootstrap` object — Tabler (jazzy_tabler) bundles Bootstrap without
            // exposing window.bootstrap, so `new bootstrap.Modal()` would throw.
            var modalEl = document.getElementById("widget-builder-modal");
            var modal = (function (el) {
                function show() {
                    el.classList.add("show");
                    el.style.display = "block";
                    el.removeAttribute("aria-hidden");
                    el.setAttribute("aria-modal", "true");
                    document.body.classList.add("modal-open");
                    var bd = document.createElement("div");
                    bd.className = "modal-backdrop fade show";
                    bd.id = "sr-modal-backdrop";
                    document.body.appendChild(bd);
                }
                function hide() {
                    el.classList.remove("show");
                    el.style.display = "none";
                    el.setAttribute("aria-hidden", "true");
                    el.removeAttribute("aria-modal");
                    document.body.classList.remove("modal-open");
                    var bd = document.getElementById("sr-modal-backdrop");
                    if (bd) bd.remove();
                }
                el.querySelectorAll('[data-bs-dismiss="modal"]').forEach(function (btn) {
                    btn.addEventListener("click", hide);
                });
                return { show: show, hide: hide };
            })(modalEl);

            function postJSON(url, payload) {
                return fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
                    body: JSON.stringify(payload),
                }).then(function (r) { return r.json(); });
            }

            // ---- live preview of placed widgets at their real widths ----
            function loadPreview($widget) {
                try {
                    $.slick_reporting.report_loader.refreshReportWidget($widget);
                } catch (e) {
                    console.error("widget preview failed to load", e);
                }
            }

            function buildCard(p) {
                var span = p.column_span || 12;
                var $col = $('<div class="col-12 col-lg-' + span + '"></div>').attr("data-saved-id", p.id);
                var $card = $('<div class="card h-100"></div>');
                var $header = $('<div class="card-header d-flex align-items-center py-1 px-2"></div>');
                $header.append('<span class="small fw-semibold text-truncate me-auto">' + escapeHtml(p.name) + "</span>");
                var $grp = $('<div class="btn-group btn-group-sm"></div>');
                $grp.append('<button type="button" class="btn btn-outline-secondary" data-act="left" title="Move earlier"><i class="fas fa-arrow-left"></i></button>');
                $grp.append('<button type="button" class="btn btn-outline-secondary" data-act="right" title="Move later"><i class="fas fa-arrow-right"></i></button>');
                $grp.append('<button type="button" class="btn btn-outline-primary" data-act="edit" title="Edit widget"><i class="fas fa-pen"></i></button>');
                $grp.append('<button type="button" class="btn btn-outline-danger" data-act="remove" title="Remove from dashboard"><i class="fas fa-times"></i></button>');
                $header.append($grp);
                $card.append($header);

                var $body = $('<div class="card-body p-2"></div>');
                var $widget = $('<div data-report-widget data-no-auto-load data-display-chart-selector="false"></div>')
                    .attr("id", "sr-preview-" + (++previewSeq))
                    .attr("data-report-url", p.report_url)
                    .attr("data-extra-params", p.extra_params || "")
                    .attr("data-chart-id", p.chart_id || "0");
                if (p.display_chart) $widget.append("<div data-report-chart></div>");
                if (p.display_table) $widget.append("<div data-report-table></div>");
                $body.append($widget);
                $card.append($body);
                $col.append($card);

                $grp.find('[data-act="left"]').on("click", function () { move(p.id, -1); });
                $grp.find('[data-act="right"]').on("click", function () { move(p.id, 1); });
                $grp.find('[data-act="edit"]').on("click", function () { openBuilder(p.report_url_name, p.id); });
                $grp.find('[data-act="remove"]').on("click", function () { removePlacement(p.id); });
                return { col: $col, widget: $widget };
            }

            function renderAll() {
                var $row = $("#dashboard-widgets").empty();
                $("#dashboard-empty").toggleClass("d-none", placements.length > 0);
                placements.forEach(function (p) {
                    var built = buildCard(p);
                    $row.append(built.col);
                    loadPreview(built.widget);
                });
                updateMoveButtons();
            }

            function updateMoveButtons() {
                var $cols = $("#dashboard-widgets > [data-saved-id]");
                $cols.each(function (i) {
                    $(this).find('[data-act="left"]').prop("disabled", i === 0);
                    $(this).find('[data-act="right"]').prop("disabled", i === $cols.length - 1);
                });
            }

            // Reorder by physically moving the DOM node (keeps its loaded chart, no refetch).
            function move(id, dir) {
                var i = placements.findIndex(function (p) { return p.id === id; });
                var j = i + dir;
                if (i < 0 || j < 0 || j >= placements.length) return;
                var tmp = placements[i];
                placements[i] = placements[j];
                placements[j] = tmp;
                var row = document.getElementById("dashboard-widgets");
                placements.forEach(function (p) {
                    var el = row.querySelector('[data-saved-id="' + p.id + '"]');
                    if (el) row.appendChild(el);
                });
                updateMoveButtons();
            }

            function removePlacement(id) {
                placements = placements.filter(function (p) { return p.id !== id; });
                renderAll();
            }

            function addPlacement(widget) {
                if (placements.some(function (p) { return p.id === widget.id; })) return;
                placements.push(widget);
                renderAll();
            }

            // ---- widget library palette ----
            function loadPalette() {
                fetch(opts.savedWidgetUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        var $pal = $("#widget-palette").empty();
                        if (!data.widgets || !data.widgets.length) {
                            $pal.append('<li class="list-group-item text-muted text-center small">No saved widgets yet.</li>');
                            return;
                        }
                        data.widgets.forEach(function (w) {
                            var $li = $(
                                '<li class="list-group-item d-flex align-items-center px-2">' +
                                '<span class="small flex-grow-1 text-truncate">' + escapeHtml(w.name) +
                                (w.shared ? ' <span class="badge bg-light text-muted">shared</span>' : "") + "</span>" +
                                '<div class="btn-group btn-group-sm">' +
                                '<button type="button" class="btn btn-outline-primary" data-act="add" title="Add to dashboard"><i class="fas fa-plus"></i></button>' +
                                '<button type="button" class="btn btn-outline-secondary" data-act="edit" title="Edit"><i class="fas fa-pen"></i></button>' +
                                "</div></li>"
                            );
                            $li.find('[data-act="add"]').on("click", function () { addPlacement(w); });
                            $li.find('[data-act="edit"]').on("click", function () { openBuilder(w.report_url_name, w.id); });
                            $pal.append($li);
                        });
                    });
            }

            // ---- builder modal ----
            var builderState = { mode: "new", widgetId: "", reportUrlName: "" };

            function resetBuilder() {
                $("#builder-report-select").val("");
                $("#builder-config").addClass("d-none");
                $("#builder-filter-form").empty();
                $("#builder-chart-select").empty();
                $("#builder-width-select").val("12");
                $("#builder-widget-name").val("");
                $("#builder-widget-id").val("");
                $("#builder-save-btn").prop("disabled", true);
            }

            function openBuilder(reportUrlName, savedWidgetId) {
                resetBuilder();
                builderState = { mode: savedWidgetId ? "edit" : "new", widgetId: savedWidgetId || "", reportUrlName: reportUrlName || "" };
                $("#builder-widget-id").val(savedWidgetId || "");
                if (reportUrlName) {
                    $("#builder-report-select").val(reportUrlName);
                    loadBuilderForm(reportUrlName, savedWidgetId);
                }
                modal.show();
            }

            function loadBuilderForm(reportUrlName, savedWidgetId) {
                if (!reportUrlName) {
                    $("#builder-config").addClass("d-none");
                    $("#builder-save-btn").prop("disabled", true);
                    return;
                }
                $("#builder-loading").removeClass("d-none");
                $("#builder-config").addClass("d-none");
                var url = opts.builderFormUrl + "?report_url_name=" + encodeURIComponent(reportUrlName);
                if (savedWidgetId) url += "&saved_widget_id=" + encodeURIComponent(savedWidgetId);
                fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        $("#builder-loading").addClass("d-none");
                        if (data.status !== "ok") {
                            alert(data.message || "Could not load report");
                            return;
                        }
                        builderState.reportUrlName = reportUrlName;
                        $("#builder-filter-form").html(data.form_html);
                        var $charts = $("#builder-chart-select").empty();
                        (data.charts || []).forEach(function (c) {
                            $charts.append('<option value="' + escapeHtml(c.id) + '">' +
                                escapeHtml(c.title) + (c.type ? " (" + escapeHtml(c.type) + ")" : "") + "</option>");
                        });
                        if (!data.charts || !data.charts.length) {
                            $charts.append('<option value="0">(no chart)</option>');
                        }
                        $charts.val(data.chart_id);
                        $("#builder-width-select").val(String(data.column_span || 12));
                        $("#builder-display-chart").prop("checked", !!data.display_chart);
                        $("#builder-display-table").prop("checked", !!data.display_table);
                        $("#builder-widget-name").val(data.name || "");
                        $("#builder-config").removeClass("d-none");
                        $("#builder-save-btn").prop("disabled", false);
                    })
                    .catch(function (err) {
                        $("#builder-loading").addClass("d-none");
                        alert("Network error: " + err);
                    });
            }

            // serialize only the injected filter form, dropping empty values
            function collectExtraParams() {
                var pairs = $("#builder-filter-form").find(":input").serializeArray();
                return pairs
                    .filter(function (p) { return p.value !== "" && p.value != null; })
                    .map(function (p) { return encodeURIComponent(p.name) + "=" + encodeURIComponent(p.value); })
                    .join("&");
            }

            // report select change -> load that report's form
            $("#builder-report-select").on("change", function () {
                loadBuilderForm(this.value, builderState.mode === "edit" ? builderState.widgetId : "");
            });

            $("#create-widget-btn").on("click", function () { openBuilder("", ""); });

            // save the widget (create or update SavedWidget)
            $("#builder-save-btn").on("click", function () {
                var reportUrlName = $("#builder-report-select").val();
                var name = ($("#builder-widget-name").val() || "").trim();
                if (!reportUrlName) { alert("Choose a report"); return; }
                if (!name) { alert("Give the widget a name"); return; }
                var wasNew = !$("#builder-widget-id").val();
                var payload = {
                    id: $("#builder-widget-id").val() || null,
                    name: name,
                    report_url_name: reportUrlName,
                    chart_id: $("#builder-chart-select").val() || "0",
                    column_span: parseInt($("#builder-width-select").val() || "12", 10),
                    display_chart: $("#builder-display-chart").is(":checked"),
                    display_table: $("#builder-display-table").is(":checked"),
                    extra_params: collectExtraParams(),
                };
                var $btn = $("#builder-save-btn").prop("disabled", true);
                postJSON(opts.savedWidgetUrl, payload)
                    .then(function (data) {
                        $btn.prop("disabled", false);
                        if (data.status !== "ok") { alert(data.message || "Save failed"); return; }
                        loadPalette();
                        var w = data.widget;
                        if (wasNew) {
                            addPlacement(w);
                        } else {
                            // update the placed widget (name/width/chart/filters) and re-render its preview
                            var i = placements.findIndex(function (p) { return p.id === w.id; });
                            if (i >= 0) placements[i] = w;
                            renderAll();
                        }
                        modal.hide();
                    })
                    .catch(function (err) { $btn.prop("disabled", false); alert("Network error: " + err); });
            });

            // save dashboard layout
            $("#save-dashboard-btn").on("click", function () {
                var $btn = $(this).prop("disabled", true).html('<i class="fas fa-spinner fa-spin me-1"></i>Saving…');
                var widgets = placements.map(function (p, i) {
                    return { saved_widget_id: p.id, order: i };
                });
                postJSON(opts.saveUrl, { widgets: widgets })
                    .then(function (data) {
                        if (data.status === "ok") {
                            window.location.href = opts.viewUrl;
                        } else {
                            alert("Save failed: " + (data.message || "Unknown error"));
                            $btn.prop("disabled", false).html('<i class="fas fa-save me-1"></i>Save dashboard');
                        }
                    })
                    .catch(function (err) {
                        alert("Network error: " + err);
                        $btn.prop("disabled", false).html('<i class="fas fa-save me-1"></i>Save dashboard');
                    });
            });

            renderAll();
            loadPalette();
        },
    };

    window.SlickDashboard = SlickDashboard;
})();
