import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

class LcaVisualizer:
    """
    Generates high-fidelity visual representations of LCA optimization
    and multi-objective trade-offs.
    """
    @staticmethod
    def generate_tradeoff_chart(report, output_path="optimization_tradeoffs.png", theme="dark"):
        """
        Creates a side-by-side normalized bar chart comparing baseline and optimized
        performance across GWP, Acidification, Water, and Feedstock Cost. Supports both light/dark theme styles.
        If the report contains a 'frontier' key, it generates a Pareto scatter plot instead.
        """
        if "frontier" in report:
            return LcaVisualizer._generate_pareto_scatter_plot(report, output_path, theme)

        metrics = report.get("metrics", {})
        if not metrics:
            print("No metrics found in report for visualization.")
            return False

        labels = list(metrics.keys())
        baseline_pcts = [100.0] * len(labels)
        
        # Calculate optimized percentages relative to baseline
        optimized_pcts = []
        for name in labels:
            details = metrics[name]
            base = details.get("baseline", 0.0)
            opt = details.get("optimized", 0.0)
            if base > 0:
                opt_pct = (opt / base) * 100.0
            else:
                opt_pct = 0.0
            optimized_pcts.append(opt_pct)

        x = np.arange(len(labels))
        width = 0.35  # width of the bars

        # Check theme color configuration
        is_light = (theme == "light")
        bg_color = '#ffffff' if is_light else '#09090b'
        card_color = '#ffffff' if is_light else '#18181b'
        border_color = '#cbd5e1' if is_light else '#27272a'
        text_primary = '#1e1e38' if is_light else '#fafafa'
        text_secondary = '#3730a3' if is_light else '#a1a1aa'
        grid_color = '#cbd5e1' if is_light else '#27272a'
        
        # Draw bars color configuration
        bar1_color = '#94a3b8' if is_light else '#27272a' # Slate 400 vs Dark Zinc
        bar1_edge = '#64748b' if is_light else '#3f3f46'  # Slate 500 vs Zinc 700
        bar2_color = '#0d9488' if is_light else '#10b981' # Teal 600 vs Emerald 500
        bar2_edge = '#0f766e' if is_light else '#059669'  # Teal 700 vs Emerald 600
        text_savings = '#0d9488' if is_light else '#34d399'
        text_base = '#64748b' if is_light else '#71717a'

        # Set up a themed, professional modern design style matching the dashboard
        fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150, facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        # Draw bars
        rects1 = ax.bar(x - width/2, baseline_pcts, width, label='Baseline', color=bar1_color, edgecolor=bar1_edge, linewidth=1)
        rects2 = ax.bar(x + width/2, optimized_pcts, width, label='Optimized (Substituted)', color=bar2_color, edgecolor=bar2_edge, linewidth=1)

        # Labels, title and custom x-axis tick labels
        ax.set_ylabel('Percentage of Baseline (%)', fontsize=11, fontweight='bold', labelpad=10, color=text_primary)
        ax.set_title(f"Trade-Off Analysis: {report.get('process_name', 'Process Substitution')}\n"
                     f"Substitute: '{report.get('substituted_from', 'Virgin')}' -> '{report.get('substituted_to', 'Recycled')}'",
                     fontsize=12, fontweight='bold', pad=15, color=text_primary)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10, fontweight='semibold', color=text_secondary)
        
        # Style legend
        legend = ax.legend(frameon=True, facecolor=card_color, edgecolor=border_color, loc='upper right')
        for text in legend.get_texts():
            text.set_color(text_primary)
            
        # Style axes and spines
        ax.tick_params(colors=text_secondary, which='both', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(border_color)
        
        # Set y-axis limit with some room for labels
        ax.set_ylim(0, 130)
        
        # Add grid lines matching theme
        ax.grid(axis='y', linestyle='--', color=grid_color, alpha=0.6)
        ax.grid(axis='x', visible=False)
        
        # Add labels on top of the bars showing the exact reduction percentages
        def autolabel(rects, is_opt=False):
            for rect in rects:
                height = rect.get_height()
                if is_opt:
                    label_text = f"{height:.1f}%"
                    # Highlight savings
                    change = height - 100.0
                    if change != 0:
                        label_text += f"\n({change:+.1f}%)"
                    ax.annotate(label_text,
                                xy=(rect.get_x() + rect.get_width() / 2, height),
                                xytext=(0, 4),  # 4 points vertical offset
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=8, fontweight='bold', color=text_savings)
                else:
                    ax.annotate('100.0%',
                                xy=(rect.get_x() + rect.get_width() / 2, height),
                                xytext=(0, 4),
                                textcoords="offset points",
                                ha='center', va='bottom', fontsize=8, color=text_base)

        autolabel(rects1)
        autolabel(rects2, is_opt=True)

        fig.tight_layout()
        
        # Save figure
        plt.savefig(output_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        print(f" -> Optimization comparison chart successfully generated and saved to: {output_path} (theme: {theme})")
        return True

    @staticmethod
    def generate_uncertainty_chart(report, output_path="uncertainty_distribution.png", metric_name="Global Warming", theme="dark"):
        """
        Creates a stochastically-resolved histogram comparison comparing baseline and optimized
        Monte Carlo distribution trials for a specific metric (e.g. GWP, Acidification, Water, Cost).
        Displays mean lines and confidence intervals.
        """
        metrics = report.get("metrics", {})
        metric_data = metrics.get(metric_name, {})
        if not metric_data:
            # Fallback to search case-insensitive
            for k in metrics.keys():
                if metric_name.lower() in k.lower():
                    metric_data = metrics[k]
                    metric_name = k
                    break
            if not metric_data and metrics:
                metric_data = list(metrics.values())[0]
                
        if not metric_data:
            print(f"No metric data found for '{metric_name}' in uncertainty distribution plot.")
            return False
            
        base_trials = metric_data.get("baseline_uncertainty", {}).get("trials", [])
        opt_trials = metric_data.get("optimized_uncertainty", {}).get("trials", [])
        
        if not base_trials or not opt_trials:
            print(f"No raw Monte Carlo trials found in '{metric_name}' metrics for plotting.")
            return False

        # Check theme color configuration
        is_light = (theme == "light")
        bg_color = '#ffffff' if is_light else '#09090b'
        card_color = '#ffffff' if is_light else '#18181b'
        border_color = '#cbd5e1' if is_light else '#27272a'
        text_primary = '#1e1e38' if is_light else '#fafafa'
        text_secondary = '#3730a3' if is_light else '#a1a1aa'
        grid_color = '#cbd5e1' if is_light else '#27272a'
        
        # Colors for baseline (zinc/grey) and optimized (emerald green)
        base_color = '#94a3b8' if is_light else '#52525b'
        opt_color = '#0d9488' if is_light else '#10b981'
        
        fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150, facecolor=bg_color)
        ax.set_facecolor(bg_color)
        
        # Plot histograms
        ax.hist(base_trials, bins=40, alpha=0.5, label=f'Baseline {metric_name} Dist', color=base_color, edgecolor=border_color, linewidth=0.5)
        ax.hist(opt_trials, bins=40, alpha=0.7, label=f'Optimized {metric_name} Dist', color=opt_color, edgecolor=opt_color, linewidth=0.5)
        
        # Draw mean vertical lines
        base_mean = sum(base_trials) / len(base_trials)
        opt_mean = sum(opt_trials) / len(opt_trials)
        ax.axvline(base_mean, color=base_color, linestyle='--', linewidth=1.5, label=f'Baseline Mean ({base_mean:.4f})')
        ax.axvline(opt_mean, color=opt_color, linestyle='--', linewidth=1.5, label=f'Optimized Mean ({opt_mean:.4f})')
        
        # Label axes
        unit = metric_data.get("unit", "")
        ax.set_xlabel(f'{metric_name} ({unit})' if unit else metric_name, fontsize=11, fontweight='bold', labelpad=10, color=text_primary)
        ax.set_ylabel('Trial Frequency (Counts)', fontsize=11, fontweight='bold', labelpad=10, color=text_primary)
        ax.set_title(f"Uncertainty Propagation: {report.get('process_name', 'Process Substitution')}\n"
                     f"Stochastic Monte Carlo Simulation ({len(base_trials)} Trials)",
                     fontsize=12, fontweight='bold', pad=15, color=text_primary)
                     
        # Legend style
        legend = ax.legend(frameon=True, facecolor=card_color, edgecolor=border_color, loc='upper right')
        for text in legend.get_texts():
            text.set_color(text_primary)
            
        # Style axes and grid
        ax.tick_params(colors=text_secondary, which='both', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(border_color)
        ax.grid(axis='y', linestyle='--', color=grid_color, alpha=0.6)
        
        fig.tight_layout()
        plt.savefig(output_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        print(f" -> Uncertainty distribution chart generated for '{metric_name}' and saved to: {output_path} (theme: {theme})")
        return True

    @staticmethod
    def _generate_pareto_scatter_plot(report, output_path, theme="dark"):
        import matplotlib.pyplot as plt
        import numpy as np

        frontier = report.get("frontier", [])
        weights = report.get("weights", {})
        process_name = report.get("process_name", "Process Optimization")

        if not frontier:
            print("No frontier data for Pareto scatter plot.")
            return False

        # Extract metrics: Cost on X axis, GWP on Y axis
        costs = [pt["metrics"]["Cost"] for pt in frontier]
        gwps = [pt["metrics"]["GWP"] for pt in frontier]
        scores = [pt.get("topsis_score", 0.5) for pt in frontier]

        # Identify the optimal point (topsis_rank == 1 or max score)
        opt_idx = 0
        max_score = -1.0
        for idx, pt in enumerate(frontier):
            if pt.get("topsis_rank") == 1:
                opt_idx = idx
                break
            if pt.get("topsis_score", 0.0) > max_score:
                max_score = pt.get("topsis_score", 0.0)
                opt_idx = idx

        opt_pt = frontier[opt_idx]
        opt_cost = opt_pt["metrics"]["Cost"]
        opt_gwp = opt_pt["metrics"]["GWP"]

        is_light = (theme == "light")
        bg_color = '#ffffff' if is_light else '#09090b'
        card_color = '#ffffff' if is_light else '#18181b'
        border_color = '#cbd5e1' if is_light else '#27272a'
        text_primary = '#1e1e38' if is_light else '#fafafa'
        text_secondary = '#3730a3' if is_light else '#a1a1aa'
        grid_color = '#cbd5e1' if is_light else '#27272a'

        fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150, facecolor=bg_color)
        ax.set_facecolor(bg_color)

        # Draw scatter points, color-coded by TOPSIS score
        cmap = plt.cm.viridis if is_light else plt.cm.plasma
        scatter = ax.scatter(costs, gwps, c=scores, cmap=cmap, s=50, alpha=0.8, edgecolors=border_color, linewidth=0.5, label="Pareto Alternatives")

        # Color bar
        cbar = fig.colorbar(scatter, ax=ax)
        cbar.set_label("TOPSIS Closeness Score", color=text_primary, fontsize=9, fontweight='semibold')
        cbar.ax.tick_params(labelsize=8, colors=text_secondary)
        cbar.outline.set_edgecolor(border_color)

        # Highlight the optimal configuration
        ax.scatter(opt_cost, opt_gwp, color='#fbbf24', edgecolors='black', marker='*', s=250, zorder=5, label=f"TOPSIS Optimal (Score: {opt_pt.get('topsis_score', 0.0):.4f})")

        # Annotate the optimal point with ratio summaries
        blend_summary = []
        for name, r in opt_pt["ratios"].items():
            short_name = name.split(',')[0]
            blend_summary.append(f"{short_name}: {r*100:.0f}%")
        blend_label = "\n".join(blend_summary)

        ax.annotate(f"Optimal Blend:\n{blend_label}",
                    xy=(opt_cost, opt_gwp),
                    xytext=(15, -15),
                    textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", color='#fbbf24', connectionstyle="arc3,rad=0.2"),
                    fontsize=9, fontweight='bold', color='#fbbf24',
                    bbox=dict(boxstyle="round,pad=0.3", fc=card_color, ec='#fbbf24', alpha=0.9))

        # Titles and labels
        ax.set_title(f"Pareto Frontier & TOPSIS Decision Support\nProcess: {process_name}", fontsize=12, fontweight='bold', pad=15, color=text_primary)
        ax.set_xlabel("Financial feedstock Cost (USD)", fontsize=11, fontweight='bold', labelpad=10, color=text_primary)
        ax.set_ylabel("Carbon Footprint (GWP, kg CO₂ eq)", fontsize=11, fontweight='bold', labelpad=10, color=text_primary)

        # Legend style
        legend = ax.legend(frameon=True, facecolor=card_color, edgecolor=border_color, loc='upper right')
        for text in legend.get_texts():
            text.set_color(text_primary)

        # Style axes and spines
        ax.tick_params(colors=text_secondary, which='both', labelsize=9)
        for spine in ax.spines.values():
            spine.set_color(border_color)

        ax.grid(True, linestyle='--', color=grid_color, alpha=0.6)

        fig.tight_layout()
        plt.savefig(output_path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        print(f" -> Pareto scatter plot successfully generated and saved to: {output_path} (theme: {theme})")
        return True
