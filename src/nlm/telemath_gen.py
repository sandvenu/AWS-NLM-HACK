"""Seeded generator of telecom numerical problems (TeleMath-style) with exact answers.

Each family draws parameters from a seeded RNG, renders a question in plain English,
computes the reference answer in Python and writes a short worked solution. Nothing here
is model-generated, so the labels are independent of every model under test. The worked
solution is used only for training items; test items are graded on the answer alone.

Usage:
  python -m nlm.telemath_gen --seed 7101 --n 400 --out testsets/execution_telemath_synth.jsonl
"""
import argparse
import hashlib
import json
import math
import random


def _r(rng, lo, hi, nd=2):
    return round(rng.uniform(lo, hi), nd)


def g(x):
    return f"{x:.6g}"


def shannon_capacity(rng):
    bw = rng.choice([1.4, 3, 5, 10, 15, 20, 40, 100])
    snr_db = _r(rng, -5, 30, 1)
    snr = 10 ** (snr_db / 10)
    cap = bw * math.log2(1 + snr)
    q = (f"A channel has a bandwidth of {bw} MHz and a signal-to-noise ratio of {snr_db} dB. "
         "Using the Shannon formula, what is the channel capacity in Mbit/s?")
    w = f"C = B log2(1 + SNR). SNR = 10^({snr_db}/10) = {g(snr)}.\nC = {bw} * log2(1 + {g(snr)}) = {g(cap)} Mbit/s."
    return q, cap, "Mbit/s", w


def fspl(rng):
    f = rng.choice([700, 900, 1800, 2100, 2600, 3500, 28000])
    d = _r(rng, 0.1, 20, 2)
    loss = 20 * math.log10(d) + 20 * math.log10(f) + 32.44
    q = (f"What is the free-space path loss in dB for a {f} MHz signal over a distance of {d} km? "
         "Use FSPL(dB) = 20 log10(d_km) + 20 log10(f_MHz) + 32.44.")
    w = (f"20 log10({d}) = {g(20 * math.log10(d))}; 20 log10({f}) = {g(20 * math.log10(f))}.\n"
         f"FSPL = {g(20 * math.log10(d))} + {g(20 * math.log10(f))} + 32.44 = {g(loss)} dB.")
    return q, loss, "dB", w


def received_power(rng):
    pt = _r(rng, 10, 46, 1)
    gt = _r(rng, 0, 18, 1)
    gr = _r(rng, 0, 5, 1)
    pl = _r(rng, 80, 140, 1)
    pr = pt + gt + gr - pl
    q = (f"A transmitter outputs {pt} dBm into an antenna with {gt} dBi gain. The receive antenna gain is "
         f"{gr} dBi and the total path loss is {pl} dB. What is the received power in dBm?")
    w = f"Pr = Pt + Gt + Gr - PL = {pt} + {gt} + {gr} - {pl} = {g(pr)} dBm."
    return q, pr, "dBm", w


def thermal_noise(rng):
    bw = rng.choice([180e3, 1.08e6, 5e6, 10e6, 20e6, 100e6])
    nf = _r(rng, 2, 9, 2)
    n = -174 + 10 * math.log10(bw) + nf
    q = (f"A receiver has a bandwidth of {bw / 1e6:g} MHz and a noise figure of {nf} dB. Assuming thermal noise "
         "density of -174 dBm/Hz, what is the receiver noise floor in dBm?")
    w = f"N = -174 + 10 log10(B_Hz) + NF = -174 + 10 log10({bw:g}) + {nf} = -174 + {g(10 * math.log10(bw))} + {nf} = {g(n)} dBm."
    return q, n, "dBm", w


def dbm_to_mw(rng):
    p = _r(rng, -30, 46, 1)
    v = 10 ** (p / 10)
    q = f"Convert a power level of {p} dBm to milliwatts."
    return q, v, "mW", f"P_mW = 10^(P_dBm/10) = 10^({p}/10) = {g(v)} mW."


def mw_to_dbm(rng):
    p = round(10 ** rng.uniform(-3, 4.5), 4)
    v = 10 * math.log10(p)
    q = f"Convert a power of {p} mW to dBm."
    return q, v, "dBm", f"P_dBm = 10 log10(P_mW) = 10 log10({p}) = {g(v)} dBm."


def wavelength(rng):
    f = rng.randrange(400, 40000, 10)
    lam = 3e8 / (f * 1e6) * 100
    q = f"What is the wavelength in centimetres of a {f} MHz carrier? Use c = 3e8 m/s."
    return q, lam, "cm", f"lambda = c/f = 3e8 / {f}e6 = {g(lam / 100)} m = {g(lam)} cm."


def propagation_delay(rng):
    d = _r(rng, 1, 2000, 1)
    v = rng.choice([2e8, 3e8])
    t = d * 1e3 / v * 1e6
    medium = "optical fibre (propagation speed 2e8 m/s)" if v == 2e8 else "free space (propagation speed 3e8 m/s)"
    q = f"What is the one-way propagation delay in microseconds over {d} km of {medium}?"
    return q, t, "us", f"t = d/v = {d * 1e3:g} m / {v:g} m/s = {g(t / 1e6)} s = {g(t)} us."


def ofdm_symbol(rng):
    mu = rng.choice([0, 1, 2, 3, 4])
    k = rng.randint(1, 140)
    scs = 15 * 2 ** mu
    tu = 1e3 / scs
    q = (f"In 5G NR with numerology mu = {mu}, the subcarrier spacing is 15*2^mu kHz. What is the total useful "
         f"duration of {k} OFDM symbols (excluding cyclic prefix) in microseconds?")
    w = f"SCS = 15 * 2^{mu} = {scs} kHz. T_u = 1/SCS = {g(tu)} us. Total = {k} * {g(tu)} = {g(k * tu)} us."
    return q, k * tu, "us", w


def nr_slots_count(rng):
    mu = rng.choice([0, 1, 2, 3, 4])
    t = rng.randint(1, 200)
    v = t * 2 ** mu
    q = (f"In 5G NR each 1 ms subframe contains 2^mu slots. How many slots are transmitted in {t} ms "
         f"for numerology mu = {mu}?")
    return q, float(v), "slots", f"Slots per subframe = 2^{mu} = {2 ** mu}; {t} subframes give {t} * {2 ** mu} = {v} slots."


def prb_count(rng):
    bw, scs = rng.choice([(5, 15), (10, 15), (20, 15), (20, 30), (40, 30), (100, 30), (50, 15), (100, 60)])
    guard_frac = _r(rng, 0.02, 0.1, 3)
    usable = bw * 1e3 * (1 - guard_frac)
    n = math.floor(usable / (12 * scs))
    q = (f"A {bw} MHz carrier reserves {guard_frac * 100:.1f}% of its bandwidth as guard band. With a subcarrier "
         f"spacing of {scs} kHz and 12 subcarriers per resource block, how many whole resource blocks fit in the "
         "usable bandwidth?")
    w = (f"Usable = {bw * 1e3:g} kHz * (1 - {guard_frac}) = {g(usable)} kHz. One RB = 12 * {scs} = {12 * scs} kHz.\n"
         f"N = floor({g(usable)} / {12 * scs}) = {n}.")
    return q, float(n), "PRBs", w


def peak_rate(rng):
    layers = rng.choice([1, 2, 4])
    qm = rng.choice([2, 4, 6, 8])
    rate = rng.choice([0.5, 0.65, 0.75, 0.9])
    nprb = rng.choice([25, 52, 106, 133, 273])
    scs = rng.choice([15, 30])
    ts = 1e-3 / (14 * scs / 15)
    oh = rng.choice([0.08, 0.14])
    r = layers * qm * rate * nprb * 12 / ts * (1 - oh) / 1e6
    q = (f"Estimate a 5G NR data rate in Mbit/s: {layers} MIMO layers, modulation order Qm = {qm}, code rate "
         f"{rate}, {nprb} resource blocks of 12 subcarriers, subcarrier spacing {scs} kHz (average OFDM symbol "
         f"duration = 1e-3 / (14 * {scs}/15) s) and an overhead fraction of {oh}. "
         "Rate = layers * Qm * code_rate * N_PRB * 12 / T_symbol * (1 - overhead).")
    w = (f"T_symbol = 1e-3 / (14 * {scs}/15) = {g(ts)} s.\n"
         f"Rate = {layers} * {qm} * {rate} * {nprb} * 12 / {g(ts)} * (1 - {oh}) = {g(r * 1e6)} bit/s = {g(r)} Mbit/s.")
    return q, r, "Mbit/s", w


def spectral_efficiency(rng):
    thr = _r(rng, 5, 600, 1)
    bw = rng.choice([5, 10, 20, 40, 100])
    q = f"A cell carries {thr} Mbit/s in {bw} MHz of spectrum. What is its spectral efficiency in bit/s/Hz?"
    return q, thr / bw, "bit/s/Hz", f"SE = throughput / bandwidth = {thr} / {bw} = {g(thr / bw)} bit/s/Hz."


def file_transfer(rng):
    size = _r(rng, 1, 5000, 1)
    rate = _r(rng, 1, 1000, 1)
    t = size * 8 / rate
    q = f"How many seconds does it take to transfer a {size} MB file over a {rate} Mbit/s link (1 MB = 8 Mbit)?"
    return q, t, "s", f"Bits = {size} * 8 = {g(size * 8)} Mbit. t = {g(size * 8)} / {rate} = {g(t)} s."


def mm1_sojourn(rng):
    mu = _r(rng, 50, 500, 1)
    lam = round(mu * rng.uniform(0.2, 0.95), 1)
    t = 1 / (mu - lam) * 1e3
    q = (f"Packets arrive at a router as a Poisson process at {lam} packets/s and are served with exponential "
         f"service at {mu} packets/s (M/M/1). What is the mean time a packet spends in the system in milliseconds?")
    return q, t, "ms", f"W = 1/(mu - lambda) = 1/({mu} - {lam}) = {g(t / 1e3)} s = {g(t)} ms."


def mm1_queue_length(rng):
    rho = _r(rng, 0.1, 0.95, 3)
    v = rho / (1 - rho)
    q = f"An M/M/1 queue has utilisation rho = {rho}. What is the mean number of customers in the system?"
    return q, v, "customers", f"L = rho/(1 - rho) = {rho}/(1 - {rho}) = {g(v)}."


def erlang_load(rng):
    calls = rng.randint(100, 5000)
    hold = _r(rng, 60, 300, 0)
    a = calls * hold / 3600
    q = (f"A cell receives {calls} calls per hour with a mean holding time of {hold:g} seconds. "
         "What is the offered traffic in Erlangs?")
    return q, a, "Erl", f"A = calls/hour * holding time / 3600 = {calls} * {hold:g} / 3600 = {g(a)} Erl."


def packet_success(rng):
    ber = float(f"{10 ** rng.uniform(-7, -3):.2e}")
    bits = rng.choice([256, 512, 1024, 1500 * 8, 9000 * 8])
    p = (1 - ber) ** bits
    q = (f"Bit errors are independent with bit error rate {ber:.2e}. What is the probability that a {bits}-bit "
         "packet is received with no bit errors?")
    return q, p, "probability", f"P = (1 - BER)^n = (1 - {ber:.2e})^{bits} = {g(p)}."


def doppler(rng):
    v = rng.randint(3, 500)
    f = rng.choice([700, 900, 2100, 2600, 3500, 4700, 28000, 39000])
    fd = v / 3.6 * f * 1e6 / 3e8
    q = f"What is the maximum Doppler shift in Hz for a user moving at {v} km/h on a {f} MHz carrier? Use c = 3e8 m/s."
    return q, fd, "Hz", f"v = {v}/3.6 = {g(v / 3.6)} m/s. f_d = v f / c = {g(v / 3.6)} * {f}e6 / 3e8 = {g(fd)} Hz."


def eirp(rng):
    p_w = rng.choice([1, 5, 10, 20, 40, 80])
    gain = _r(rng, 5, 21, 1)
    loss = _r(rng, 0.5, 4, 1)
    p_dbm = 10 * math.log10(p_w * 1000)
    e = p_dbm + gain - loss
    q = (f"A {p_w} W transmitter feeds an antenna with {gain} dBi gain through cables with {loss} dB loss. "
         "What is the EIRP in dBm?")
    return q, e, "dBm", f"P = 10 log10({p_w * 1000} mW) = {g(p_dbm)} dBm. EIRP = {g(p_dbm)} + {gain} - {loss} = {g(e)} dBm."


def friis_cascade(rng):
    nf1 = _r(rng, 0.5, 3, 1)
    g1 = _r(rng, 10, 25, 1)
    nf2 = _r(rng, 3, 10, 1)
    f1 = 10 ** (nf1 / 10)
    f2 = 10 ** (nf2 / 10)
    lin_g1 = 10 ** (g1 / 10)
    ftot = f1 + (f2 - 1) / lin_g1
    nf = 10 * math.log10(ftot)
    q = (f"A low-noise amplifier with noise figure {nf1} dB and gain {g1} dB is followed by a mixer with noise "
         f"figure {nf2} dB. Using the Friis formula, what is the cascade noise figure in dB?")
    w = (f"F1 = 10^({nf1}/10) = {g(f1)}, G1 = 10^({g1}/10) = {g(lin_g1)}, F2 = 10^({nf2}/10) = {g(f2)}.\n"
         f"F = F1 + (F2 - 1)/G1 = {g(ftot)}. NF = 10 log10({g(ftot)}) = {g(nf)} dB.")
    return q, nf, "dB", w


def log_distance(rng):
    pl0 = _r(rng, 30, 45, 1)
    n = _r(rng, 2, 4.5, 1)
    d = _r(rng, 10, 2000, 0)
    pl = pl0 + 10 * n * math.log10(d)
    q = (f"Using a log-distance path loss model with PL(1 m) = {pl0} dB and path loss exponent {n}, what is "
         f"the path loss in dB at {d:g} m?")
    return q, pl, "dB", f"PL = PL0 + 10 n log10(d/1 m) = {pl0} + 10 * {n} * {g(math.log10(d))} = {g(pl)} dB."


def cell_radius(rng):
    mapl = _r(rng, 110, 150, 1)
    a, b = rng.choice([(128.1, 37.6), (120.9, 37.6), (133.0, 38.3)])
    r = 10 ** ((mapl - a) / b)
    q = (f"The urban path loss model is PL(dB) = {a} + {b} log10(R_km). If the maximum allowable path loss is "
         f"{mapl} dB, what is the cell radius in km?")
    return q, r, "km", f"log10(R) = ({mapl} - {a}) / {b} = {g((mapl - a) / b)}. R = 10^{g((mapl - a) / b)} = {g(r)} km."


def arq_goodput(rng):
    rate = rng.choice([1, 2, 5, 10, 20, 50, 100, 200])
    per = _r(rng, 0.01, 0.4, 3)
    gp = rate * (1 - per)
    q = (f"A link transmits at {rate} Mbit/s with selective-repeat ARQ and a packet error rate of {per}. "
         "Ignoring protocol overhead, what is the goodput in Mbit/s?")
    return q, gp, "Mbit/s", f"Goodput = R (1 - PER) = {rate} * (1 - {per}) = {g(gp)} Mbit/s."


FAMILIES = [shannon_capacity, fspl, received_power, thermal_noise, dbm_to_mw, mw_to_dbm, wavelength,
            propagation_delay, ofdm_symbol, nr_slots_count, prb_count, peak_rate, spectral_efficiency,
            file_transfer, mm1_sojourn, mm1_queue_length, erlang_load, packet_success, doppler, eirp,
            friis_cascade, log_distance, cell_radius, arq_goodput]


def question_hash(q):
    return hashlib.sha256(q.strip().lower().encode()).hexdigest()


def generate(seed, n, prefix, banned=frozenset(), with_work=False):
    rng = random.Random(seed)
    items, seen = [], set(banned)
    while len(items) < n:
        fam = FAMILIES[len(items) % len(FAMILIES)]
        for _ in range(1000):
            q, a, unit, work = fam(rng)
            h = question_hash(q)
            if h not in seen:
                break
        else:
            raise RuntimeError(f"family {fam.__name__} cannot produce a new unique question")
        seen.add(h)
        item = {"id": f"{prefix}-{len(items):04d}", "family": fam.__name__, "question": q,
                "answer": float(g(a)), "unit": unit}
        if with_work:
            item["work"] = f"{work}\nFinal answer: {g(a)}"
        items.append(item)
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--prefix", default="exe")
    ap.add_argument("--exclude", default="", help="JSONL whose questions must never be generated (the frozen test set)")
    ap.add_argument("--with-work", action="store_true", help="add worked solutions (training data only)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    banned = frozenset()
    if args.exclude:
        with open(args.exclude, encoding="utf-8") as f:
            banned = frozenset(question_hash(json.loads(l)["question"]) for l in f if l.strip())
    items = generate(args.seed, args.n, args.prefix, banned, args.with_work)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"wrote {len(items)} items to {args.out} (excluded {len(banned)} banned question hashes)")


if __name__ == "__main__":
    main()
