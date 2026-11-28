# Taktike protivnika (simulator)

Fajl ovde = taktika za protivnika u simulatoru (veliki robot ili PAMI). Piše se kao naša taktika (Gambit Micro:
`goto`, `move`, `turn_to`, `wait`, `wait_until`, `match_time`...) **za žutu stranu**; simulator je sam ogleda na
protivnikovu stranu. Bez `START` protivnik kreće sa mesta gde je postavljen na stolu (PAMI).

Protivnik ide po putanji izračunatoj unapred: kad bi udario u naš robot stoji i čeka, kamenolome gura. Vreme
teče od činča (`match_time()`), pa PAMI može da čeka poslednjih 15 s: `wait_until(lambda: match_time() >= 85, 100)`.
`random` je ponovljiv (seme u podešavanju protivnika).
