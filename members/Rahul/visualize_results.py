"""Create a static, shareable plot from a case's benchmark exports."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results'
PLOTS = ROOT / 'plots'
REPORTS = ROOT / 'reports'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', default='TC11', help='Source filename stem')
    args = parser.parse_args()
    stem = args.case
    if Path(stem).name != stem or not stem.startswith('TC') or not stem[2:].isdigit():
        parser.error('Use a case filename stem such as TC11')
    case = json.loads((ROOT / 'test_cases' / (stem + '.json')).read_text(encoding='utf-8-sig'))
    rows = list(csv.DictReader((RESULTS / (stem + '_results.csv')).open(encoding='utf-8')))
    saved = json.loads((RESULTS / (stem + '_routes.json')).read_text(encoding='utf-8'))[0]
    methods = ['GREEDY', 'SB', 'SA']
    records = {r['algorithm']: r for r in rows}
    nodes = {n['id']: n for n in [case['depot']] + case['customers']}
    depot = case['depot']['id']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig = plt.figure(figsize=(17, 10), facecolor='#f5f7fb')
    grid = fig.add_gridspec(2, 6, height_ratios=[1, 1.85], hspace=.42, wspace=.7)
    cost_ax = fig.add_subplot(grid[0, :3])
    time_ax = fig.add_subplot(grid[0, 3:])
    colors = ['#64748b', '#2563eb', '#059669']
    weighted = records['SB'].get('objective') == 'weighted'
    score_key = 'objective_cost' if weighted else 'final_travel_minutes'
    costs = [float(records[m][score_key]) for m in methods]
    totals = [float(records[m]['total_seconds']) for m in methods]
    for ax, values, title, label in [
            (cost_ax, costs, 'Weighted objective' if weighted else 'Travel time — lower is better',
             'Objective score' if weighted else 'Travel minutes'),
            (time_ax, totals, 'Compute time for this run', 'Seconds')]:
        bars = ax.bar(methods, values, color=colors, width=.55)
        ax.set_title(title, loc='left', fontweight='bold', pad=12)
        ax.set_ylabel(label)
        ax.set_ylim(0, max(values) * 1.22)
        ax.grid(axis='y', alpha=.15)
        ax.set_axisbelow(True)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, value + max(values)*.025,
                    f'{value:.2f}' if ax is cost_ax else f'{value:.4f}', ha='center')
    palette = plt.get_cmap('tab10')
    for index, method in enumerate(methods):
        ax = fig.add_subplot(grid[1, index*2:(index+1)*2])
        result = saved['algorithms'][method]
        for vehicle_index, route in enumerate(result['routes']):
            if not route['customers']:
                continue
            sequence = [depot] + route['customers'] + [depot]
            xs = [nodes[n]['x'] for n in sequence]
            ys = [nodes[n]['y'] for n in sequence]
            color = palette(vehicle_index % 10)
            ax.plot(xs, ys, color=color, linewidth=1.35, alpha=.85)
            ax.scatter(xs[1:-1], ys[1:-1], color=color, s=19, zorder=3)
        unserved = result['unserved_ids']
        if unserved:
            ax.scatter([nodes[n]['x'] for n in unserved],
                       [nodes[n]['y'] for n in unserved], marker='x',
                       color='#dc2626', s=65, linewidths=2, zorder=4)
        for customer in case['customers']:
            ax.annotate(str(customer['id']), (customer['x'], customer['y']),
                        xytext=(3, 3), textcoords='offset points', fontsize=6, color='#334155')
        ax.scatter([case['depot']['x']], [case['depot']['y']], marker='*',
                   color='#111827', s=190, edgecolors='white', zorder=5)
        improvement = (costs[0]-costs[index])/costs[0]*100 if costs[0] else 0
        cost_label = ('score' if weighted else 'min') + ('' if result['feasible'] else ' (partial routes)')
        ax.set_title(f'{method} | {costs[index]:.2f} {cost_label}\n'
                     f'{improvement:.2f}% lower {"objective" if weighted else "travel"} | '
                     f'{"Feasible" if result["feasible"] else "Incomplete / infeasible"}',
                     loc='left', fontsize=11, fontweight='bold', pad=12)
        ax.set_xlabel('Synthetic X coordinate')
        ax.set_ylabel('Synthetic Y coordinate')
        ax.set_aspect('equal', adjustable='box')
        ax.set_xlim(min(n['x'] for n in nodes.values())-6, max(n['x'] for n in nodes.values())+6)
        ax.set_ylim(min(n['y'] for n in nodes.values())-6, max(n['y'] for n in nodes.values())+6)
        ax.grid(alpha=.12)
    used = [(i,v) for i,v in enumerate(case['vehicles'])
            if any(saved['algorithms'][m]['routes'][i]['customers'] for m in methods)]
    legend = [Line2D([0],[0],color=palette(i%10),label=v['id'],lw=2) for i,v in used]
    legend.append(Line2D([0],[0],color='#111827',marker='*',linestyle='',label='Depot',markersize=10))
    if any(saved['algorithms'][m]['unserved_ids'] for m in methods):
        legend.append(Line2D([0],[0],color='#dc2626',marker='x',linestyle='',
                             label='Unserved customer',markersize=8))
        cost_ax.set_title('Partial-route objective — customers remain unserved' if weighted
                         else 'Partial-route travel — customers remain unserved',
                          loc='left', fontweight='bold', pad=12)
    fig.legend(handles=legend, loc='lower center', bbox_to_anchor=(.5,.06),
               ncol=len(legend), frameon=False)
    fig.suptitle(f'Q-ORBIT: {stem}.json / internal {case["id"]} — {case["title"]}',
                 fontsize=18, fontweight='bold', x=.07, ha='left', y=.97)
    fig.text(.07,.916,f'{len(case["customers"])} customers | {len(case["vehicles"])} vehicles | '
             f'Seed {records["SB"]["seed"]} | {records["SB"]["samples"]} replicas | '
             f'{records["SB"]["steps"]} steps / sweeps | '
             f'{records["SB"]["chunk_size"]} customers per QUBO block',color='#475569')
    if 'passes' in records['SB']:
        fig.text(.07,.89,f'Adaptive passes: {records["SB"]["passes"]} | '
                 f'Window stride: {records["SB"]["stride"]} | '
                 f'Restarts per window: {records["SB"]["restarts"]} | '
                 'QUBOs refreshed from current routes',fontsize=10,color='#475569')
    fig.text(.07,.028,'Routes show synthetic straight-line coordinates, not road geometry. '
             'SB and SA reorder route windows; customer-to-vehicle assignments stay fixed.',
             fontsize=9,color='#475569')
    fig.text(.07,.012,'SB steps and SA sweeps do different amounts of work. '
             'Timing includes greedy initialization, QUBO preparation, solving and decoding; excludes file I/O.',
             fontsize=9,color='#475569')
    fig.subplots_adjust(left=.07,right=.97,top=.85,bottom=.15)
    for suffix in ['png','svg']:
        PLOTS.mkdir(parents=True, exist_ok=True)
        target = PLOTS / (stem + '_comparison.' + suffix)
        fig.savefig(target,dpi=180,facecolor=fig.get_facecolor())
        print(target.name)
    plt.close(fig)
    report = [f'# {stem}.json — internal {case["id"]}', '',
              f'![Route and cost comparison](../plots/{stem}_comparison.png)', '',
              f'| Algorithm | {"Objective score" if weighted else "Travel minutes"} | Improvement vs greedy | Feasible | Total compute seconds |',
              '|---|---:|---:|---|---:|']
    for method,cost,total in zip(methods,costs,totals):
        percent=(costs[0]-cost)/costs[0]*100 if costs[0] else 0
        report.append(f'| {method} | {cost:.2f} | {percent:.2f}% | '
                      f'{records[method]["feasible"]} | {total:.4f} |')
    if 'distance' in records['SB']:
        report += ['', '## Distance and estimated fuel', '',
                   '| Algorithm | Distance (coordinate units) | Travel minutes | Assumed km | Estimated liters | Fuel cost |',
                   '|---|---:|---:|---:|---:|---:|']
        for method in methods:
            r = records[method]
            report.append(f'| {method} | {float(r["distance"]):.6f} | {float(r["final_travel_minutes"]):.2f} | '
                          f'{float(r["distance_km"]):.6f} | {float(r["estimated_fuel_liters"]):.6f} | '
                          f'{float(r["estimated_fuel_cost"]):.6f} {r["currency"]} |')
        r = records['SB']
        report += ['', f'Assumptions: {r["km_per_unit"]} km per coordinate unit; '
                   f'{r["liters_per_100km"]} L/100 km; {r["price_per_liter"]} {r["currency"]}/L.',
                   'Distance is synthetic straight-line distance including depot legs. Fuel excludes idling and load effects.',
                   f'Objective: {r["objective"]}; weights: distance={r["distance_weight"]}, '
                   f'travel time={r["travel_time_weight"]}, fuel cost={r["fuel_weight"]}.',
                   'The weighted score combines raw units without normalization; weights set their relative influence.']
    report += ['', '## Example: V1 visiting order', '']
    for method in methods:
        route=saved['algorithms'][method]['routes'][0]
        order=' → '.join(map(str,[depot]+route['customers']+[depot]))
        report.append(f'- **{method}**: {order} ({route.get("travel_minutes", route["cost"]):.2f} travel minutes)')
    report += ['', 'Customer labels and colors match across the route maps. The star is the depot.',
               'Routes use synthetic coordinates; they are not actual road maps.',
               'This is one seeded run, not a statistical claim that SB or SA is always better.',
               'Time windows/capacity are checked after decoding; online vehicle reassignment is not implemented.', '',
               f'Raw results: [{stem}_results.csv](../results/{stem}_results.csv); '
               f'route schedules: [{stem}_routes.json](../results/{stem}_routes.json).', '']
    if 'raw_valid_percent' in records['SB']:
        report += ['', '## Search diagnostics', '',
                   '| Method | Original pass travel min | Raw valid assignments | Solver calls | Rebuilt QUBOs |',
                   '|---|---:|---:|---:|---:|']
        for method in ['SB', 'SA']:
            record = records[method]
            report.append(f'| {method} | {float(record["reference_travel_minutes"]):.2f} | '
                          f'{float(record["raw_valid_percent"]):.2f}% | '
                          f'{record["solver_calls"]} | {record["rebuilt_qubos"]} |')
        report += ['', f'Adaptive settings: {records["SB"]["passes"]} passes, '
                   f'stride {records["SB"]["stride"]}, {records["SB"]["restarts"]} seeded restarts. '
                   'Each method rebuilds QUBOs from its own accepted route. '
                   'These runs do not have matched wall-clock budgets.']
    for method in methods:
        unserved = saved['algorithms'][method]['unserved_ids']
        if unserved:
            report.append(f'**{method}: unserved customer IDs {unserved}.** '
                          'Red crosses mark these customers. Travel costs cover partial routes; '
                          'cost reductions do not represent a complete feasible solution.')
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / (stem+'_report.md')).write_text('\n'.join(report),encoding='utf-8')
    print(stem+'_report.md')

if __name__ == '__main__':
    main()
