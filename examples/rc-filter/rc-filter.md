---
title: Anti-alias filter
section: "4.2"
tab: SIG
handbook: Operations Handbook
system: Signal conditioning
doc: SIG-4.2
mission: EXAMPLE-1
date: 10.27.2026
change: 10.27.2026
by: an engineering section with a block diagram, math, a log-frequency plot and a parts table
---

## Functional description

Each sensor channel passes through a cascade of first-order RC sections ahead of the converter. The cascade
removes energy above the Nyquist frequency so that it cannot fold back into the measurement band.

:::diagram Signal Conditioning Channel, One of Eight
grid 1.7 0.8
node sns "sensor" 0 0 dash
node buf "buffer\namp" 1 0
node rc1 "rc\nsection 1" 2 0
node rc2 "rc\nsection 2" 3 0
node adc "converter\n16 bit" 4 0
node log "telemetry\nbuffer" 4 1 drum
fence "filter cascade" rc1 rc2
edge sns buf "0 to 5 v"
edge buf rc1
edge rc1 rc2
edge rc2 adc
edge adc log "8 kS/s"
:::

### Transfer function

One section passes a fraction of the input set by the ratio of frequency to the corner frequency $f_c$:

$$H(f) = \frac{1}{1 + j f / f_c}, \qquad f_c = \frac{1}{2 \pi R C}$$

With $R = 1.6\ \mathrm{k\Omega}$ and $C = 100\ \mathrm{nF}$ the corner is $f_c \approx 1.0\ \mathrm{kHz}$. Each section adds
6 dB per octave of rolloff above the corner (figure 4.2-2).

::::row
:::plot Magnitude Response of One, Two and Four Sections
csv bode.csv
x hz "frequency, hz"
y first "1 section"
y second "2 sections"
y fourth "4 sections"
ylabel "gain, db"
log x
mark 1000 "fc"
mark 4000 "nyquist"
:::
|||
:::table Section Parts
| Ref | Value | Tol | Note |
|---|---|---|---|
| R1, R2 | 1.6 k | 1 % | metal film |
| C1, C2 | 100 nF | 5 % | C0G |
| U1 | -- | -- | rail-to-rail buffer |
:::

:::caution
Do not substitute X7R capacitors. Their value falls with applied voltage and moves the corner.
:::
::::

## Verification

:::checklist Channel response check | Test
SIG GEN ............... 1 KHZ, 1 V RMS
CHAN 1 OUTPUT ......... -3 DB +/- 0.5
SIG GEN ............... 4 KHZ
CHAN 1 OUTPUT ......... -24 DB OR LESS
REPEAT ................ CHAN 2 THRU 8
:::
