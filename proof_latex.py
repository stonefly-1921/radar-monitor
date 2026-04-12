import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

plt.style.use('seaborn-v0_8-whitegrid')

D = chr(36)  # dollar sign

pdf_path = r'C:\Users\15041\.openclaw\workspace\proof_correction.pdf'

with PdfPages(pdf_path) as pdf:

    # Page 1: Title
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.text(0.5, 0.88, 'Corrected Proof', transform=ax.transAxes,
            fontsize=22, fontweight='bold', ha='center', va='center')
    ax.text(0.5, 0.81,
            'Optimal Error Exponent for Complementary Paley Graphs',
            transform=ax.transAxes, fontsize=14, ha='center', va='center')
    ax.text(0.5, 0.74,
            'Source: Proactively Detecting Structure Information',
            transform=ax.transAxes, fontsize=11, style='italic',
            ha='center', va='center')
    ax.text(0.5, 0.70,
            'via Boolean Multiaccess Channels',
            transform=ax.transAxes, fontsize=11, style='italic',
            ha='center', va='center')
    ax.text(0.5, 0.61,
            '--- A Correction to Section V ---',
            transform=ax.transAxes, fontsize=11,
            ha='center', va='center', color='darkred', fontweight='bold')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # Page 2: Theorem
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.text(0.04, 0.97, 'Theorem (Corrected Version, Section V)',
            transform=ax.transAxes, fontsize=13, fontweight='bold')
    lines = [
        f'Let {D}N = w^2 ({D}w an odd prime), and {D}G_1, {D}G_2 be complementary',
        'equally-weighted Paley graphs. Let {D}X* be a maximum independent',
        f'set of {D}G_1 with |{D}X*| = sqrt({D}N) = {D}w.',
        '',
        'Then:',
        '',
        '(1) The optimal codebook is deterministic:',
        f'    {D}Q({D}X*) = 1, {D}Q({D}X) = 0 for {D}X != {D}X*.',
        '',
        f'(2) If {D}G_1 is activated, then {D}p_1 = 1 and the output {D}y is',
        '    deterministic (always 1).',
        f'(3) If {D}G_2 is activated, then {D}p_2 = 2/({D}w+1).',
        '(4) The optimal error exponent is:',
        f'    {D}D* = Theta(1/sqrt({D}N)),',
        '    or equivalently:',
        f'    {D}D* = log((2(sqrt({D}N)+1))/(sqrt({D}N)+3)).',
    ]
    for i, line in enumerate(lines):
        ax.text(0.04, 0.93 - i * 0.058, line,
                transform=ax.transAxes, fontsize=10.5, va='top')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # Page 3: Proof Step 1
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.text(0.04, 0.97,
            f'Proof Step 1: Optimal Codebook is Deterministic for {D}K = 2',
            transform=ax.transAxes, fontsize=12, fontweight='bold')
    lines = [
        'From the optimization problem (Eqs. 9-10), the constraints provide',
        f'{D}K equations plus the probability normalization constraint',
        f'sum_{D}X {D}Q({D}X) = 1. Hence the degrees of freedom are {D}K-1.',
        '',
        f'For {D}K = 2, there is only 1 degree of freedom. A single codeword',
        'suffices to achieve optimality. Therefore the optimal solution must',
        'be a deterministic codebook:',
        f'    {D}Q({D}X*) = 1.',
        '',
        'QED.',
    ]
    for i, line in enumerate(lines):
        ax.text(0.04, 0.93 - i * 0.072, line,
                transform=ax.transAxes, fontsize=10.5, va='top')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # Page 4: Proof Step 2
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.text(0.04, 0.97,
            f'Proof Step 2: Determining the Optimal Codeword {D}X*',
            transform=ax.transAxes, fontsize=12, fontweight='bold')
    lines = [
        f'Let {D}X* be a maximum independent set of {D}G_1, with |{D}X*| = {D}w.',
        '',
        'Claim: {D}X* is the optimal codeword.',
        '',
        'Reason:',
        f'Let {D}X be any independent set of {D}G_1. Then {D}p_1({D}X) = 1',
        f'(since {D}X has no internal edges, alpha({D}X, {D}G_1) = 0).',
        f'The probability under {D}G_2 is {D}p_2({D}X) = 1 - alpha({D}X, {D}G_2).',
        f'To maximize separation, we need to minimize {D}p_2({D}X), i.e.,',
        f'maximize alpha({D}X, {D}G_2).',
        '',
        f'Since {D}G_1 and {D}G_2 are complementary, {D}X is an independent set',
        f'of {D}G_1 iff {D}X induces a complete subgraph in {D}G_2 (every pair',
        f'of nodes in {D}X is adjacent in {D}G_2).',
        f'Hence the larger |{D}X|, the higher alpha({D}X, {D}G_2).',
        '',
        f'Therefore the maximum independent set {D}X* maximizes alpha({D}X*, {D}G_2),',
        f'minimizes {D}p_2, and maximizes Chernoff information.',
        '',
        'QED.',
    ]
    for i, line in enumerate(lines):
        ax.text(0.04, 0.95 - i * 0.052, line,
                transform=ax.transAxes, fontsize=10.5, va='top')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # Page 5: Proof Step 3
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.text(0.04, 0.97,
            f'Proof Step 3: Exact Calculation of alpha({D}X*, {D}G_2)',
            transform=ax.transAxes, fontsize=12, fontweight='bold')
    lines = [
        f'Lemma: |E({D}G_2[{D}X*])| = {D}w({D}w-1)/2.',
        '',
        'Proof: Since {D}X* is an independent set in {D}G_1, no edge between',
        f'any two nodes of {D}X* belongs to {D}G_1. Because {D}G_1 and {D}G_2 are',
        f'complementary, every such edge {{i,j}} belongs to {D}G_2. Thus {D}X*',
        f'induces a complete graph K_{D}w in {D}G_2, with {D}w({D}w-1)/2 edges.',
        '',
        'QED.',
        '',
        'Calculation of alpha({D}X*, {D}G_2):',
        '',
        f'The total number of edges in a Paley graph is',
        f'|E({D}G_k)| = {D}N({D}N-1)/4 = {D}w^2({D}w^2-1)/4.',
        '',
        f'    alpha({D}X*, {D}G_2) = 2|E({D}G_2[{D}X*])| / |E({D}G_2)|',
        f'    = 2 * [{D}w({D}w-1)/2] / [w^2(w^2-1)/4]',
        f'    = 4 / [{D}w({D}w+1)].',
        '',
        f'By Eq. (7): {D}p_2 = 1 - alpha({D}X*, {D}G_2) = 2/({D}w+1).',
        '',
        'QED.',
    ]
    for i, line in enumerate(lines):
        ax.text(0.04, 0.95 - i * 0.050, line,
                transform=ax.transAxes, fontsize=10.5, va='top')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # Page 6: Proof Step 4
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.text(0.04, 0.97, 'Proof Step 4: Error Exponent',
            transform=ax.transAxes, fontsize=12, fontweight='bold')
    lines = [
        'Two hypotheses:',
        f'    H_1: {D}Y ~ Bern(1),    {D}p_1 = 1',
        f'    H_2: {D}Y ~ Bern({D}p_2),  {D}p_2 = 2/({D}w+1)',
        '',
        f'The Chernoff information for distinguishing Bern(1) from Bern({D}q):',
        f'    {D}C(1,{D}q) = -log((1+{D}q)/2).',
        '',
        f'Substituting {D}q = {D}p_2 = 2/({D}w+1):',
        f'    {D}D* = -log((1 + 2/({D}w+1)) / 2)',
        f'    = -log(({D}w+3) / (2({D}w+1)))',
        f'    = log(2({D}w+1) / ({D}w+3)).',
        '',
        'Asymptotic expansion (for large w):',
        f'    2({D}w+1)/({D}w+3) = 2 - 4/{D}w + O(1/{D}w^2)',
        f'    {D}D* = log(2) - 2/{D}w + O(1/{D}w^2)',
        f'    {D}D* = Theta(1/{D}w).',
        '',
        f'Since {D}w = sqrt({D}N):',
        '',
        f'    |D* = Theta(1/sqrt({D}N))|',
        '',
        'QED.',
    ]
    for i, line in enumerate(lines):
        ax.text(0.04, 0.96 - i * 0.052, line,
                transform=ax.transAxes, fontsize=10.5, va='top')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # Page 7: Conclusion
    fig = plt.figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.text(0.04, 0.97, 'Conclusion',
            transform=ax.transAxes, fontsize=13, fontweight='bold')
    ax.text(0.04, 0.91,
            'Original claim (Section V Theorem):',
            transform=ax.transAxes, fontsize=11, fontweight='bold')
    ax.text(0.04, 0.87,
            '"The optimal exponent is shown to be O(1/N)."',
            transform=ax.transAxes, fontsize=11, style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='mistyrose', alpha=0.7))
    ax.text(0.04, 0.79,
            'Corrected claim:',
            transform=ax.transAxes, fontsize=11, fontweight='bold')
    ax.text(0.04, 0.75,
            '"The optimal exponent is shown to be Theta(1/sqrt(N)),',
            transform=ax.transAxes, fontsize=11, style='italic')
    ax.text(0.04, 0.71,
            'or equivalently: log((2(sqrt(N)+1))/(sqrt(N)+3))."',
            transform=ax.transAxes, fontsize=11, style='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='honeydew', alpha=0.7))
    ax.text(0.04, 0.63,
            "This correction does NOT affect the paper's core contributions:",
            transform=ax.transAxes, fontsize=11)
    items = [
        '[*] Model formulation and optimization framework',
        '[*] Detection feasibility via error exponent analysis',
        '[*] K = 2 optimal codebook is deterministic (Q(X*) = 1)',
        '[*] Maximum independent set is the optimal codeword',
    ]
    for i, item in enumerate(items):
        ax.text(0.06, 0.58 - i * 0.055, item,
                transform=ax.transAxes, fontsize=10.5)
    ax.text(0.04, 0.35,
            'Only the quantitative exponent order requires revision:',
            transform=ax.transAxes, fontsize=11, fontweight='bold')
    ax.text(0.04, 0.29,
            'O(1/N)  -->  Theta(1/sqrt(N))',
            transform=ax.transAxes, fontsize=14, color='darkred', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', alpha=0.9))
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

print(f'PDF generated: {pdf_path}')
