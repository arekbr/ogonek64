# Dlaczego wolno narysować taki font

Zestaw źródeł, na których stoi ten projekt. **To nie porada prawna** — to udokumentowana
analiza ryzyka. Jeśli budujesz na tym coś komercyjnego, pogadaj z prawnikiem.

## Trzy warstwy, które trzeba rozdzielić

Większość nieporozumień w tym temacie bierze się ze zlewania trzech różnych rzeczy:

| warstwa | co to | status |
|---|---|---|
| **krój / kształt litery** | jak wygląda litera `A` | w USA niechronione |
| **plik fontowy** | konkretny `.ttf` z krzywymi, hintingiem, metrykami | chroniony — autora **tego pliku** |
| **ROM jako binarka** | 4 KB danych z układu generatora znaków | prawa do **kopii pliku**, nie do wyglądu liter |

Ten projekt nie zawiera cudzego pliku fontowego ani żadnej binarki ROM.

## Kształty liter nie podlegają prawu autorskiemu w USA

- **`37 CFR § 202.1(e)`** — wykaz materiałów niepodlegających rejestracji wymienia
  wprost *„typeface as typeface"*.
  <https://www.copyright.gov/title37/202/37cfr202-1.html>

- **Eltra Corp. v. Ringer, 579 F.2d 294 (4th Cir. 1978)** — firma zapłaciła 11 000 USD
  za zaprojektowanie kroju, Copyright Office odmówił rejestracji, sąd odmowę utrzymał:
  *„typeface is an industrial design in which the design cannot exist independently and
  separately as a work of art"*.
  <https://law.resource.org/pub/us/case/reporter/F2/579/579.F2d.294.77-1188.html>

## Ochrona pliku fontowego nie przenosi się na bitmapę

**Adobe Systems v. Southern Software** (N.D. Cal. 1998) dało ochronę *plikowi* fontowemu,
ale uzasadnienie jest tu kluczowe:

> „While the glyph dictates to a certain extent what points the editor must choose,
> it does not dictate every point that must be chosen."

<https://www.monotype.com/resources/expertise/case-fonts-copyrightability-font-software-united-states>

Ochrona wzięła się z **wyboru punktów kontrolnych krzywych Béziera**. W bitmapie 8×8
takiego wyboru nie ma — piksel jest zapalony albo nie. Ten sam test, który dał Adobe
ochronę, odmawia jej bitmapie. Compendium of U.S. Copyright Office Practices (3 wyd.,
§ 906.4) mówi to wprost: *„bitmapped font is nothing more than a computerized
representation of a typeface, and as such is not copyrightable"*.
⚠️ Ten cytat mam z opracowań prawniczych, nie z samego PDF-a Compendium — nie
weryfikowałem u źródła.

## Polska i UE

- **art. 1 ust. 1** pr. aut. — utwór to *„każdy przejaw działalności twórczej
  o indywidualnym charakterze"*. **Brak wyłączenia dla krojów pisma**, brak orzecznictwa.
  Czyli inaczej niż w USA: teoretycznie krój *może* być utworem.
- **art. 1 ust. 2** daje kontrargument: *„Ochroną objęty może być wyłącznie sposób
  wyrażenia; nie są objęte ochroną odkrycia, idee, procedury, metody i zasady
  działania"*. Przy 8 pikselach na czytelną literę sposób wyrażenia jest zdeterminowany
  funkcją, nie inwencją.
- 🔴 **art. 36 — 70 lat od śmierci twórcy.** Upływ czasu tu **nie pomaga**: krój jest
  z 1982 r., ale to nieistotne, bo termin liczy się od śmierci autora, a projektanci
  pierwowzoru żyją. Argument „stare, więc wolne" jest w polskim prawie autorskim
  po prostu nieprawdziwy.
- **Wzór przemysłowy** (rozp. Rady (WE) 6/2002) — maksymalnie **25 lat** od zgłoszenia,
  więc nawet gdyby cokolwiek zgłoszono w 1982, ochrona wygasłaby najdalej w 2007.

## Precedens praktyczny — dwa niezależne przeglądy licencyjne

Najmocniejszy argument nie jest teoretyczny:

- Pakiet **`fonts-sixtyfour`** siedzi w **Debianie `main`** (nie contrib, nie non-free),
  na **SIL OFL 1.1**, autor Jens Kutilek. Opis pakietu wprost: *„vector font similar to
  the ROM font of Commodore 64"*.
  <https://packages.debian.org/sid/all/fonts/fonts-sixtyfour> ·
  <https://sources.debian.org/src/fonts-homecomputer/1.0-3/debian/copyright/>
- **Google Fonts** przyjęło dwa fonty tej rodziny: `Sixtyfour` i `Sixtyfour Convergence`
  (COLRv1), oba OFL bez Reserved Font Name.
  <https://fonts.google.com/specimen/Sixtyfour>

Debian DFSG i Google Fonts to dwa surowe, niezależne przeglądy licencyjne — oba
przepuściły font jawnie deklarujący pochodzenie od tego kroju. Poszukiwania sporów
(DMCA, takedown, usunięte repozytoria) dały **wynik negatywny**.

## Czego ten projekt świadomie nie robi

- **Nie dystrybuuje binarki ROM** ani żadnego cudzego pliku fontowego.
- **Nie modyfikuje fonta „C64 Pro" ze style64.org.** Tamta licencja przy każdym
  dozwolonym użyciu powtarza *„without any modification"*, więc pochodna z polskimi
  znakami wypadałaby poza zgodę. Zamiast obchodzić tamtą licencję — glify są własne.
  Warto podkreślić: ta licencja dotyczy **wyłącznie ich plików** i nie rości sobie
  żadnych praw do kształtów liter.
- **Nie używa znaków towarowych w nazwach fontów.** Marka Commodore ma właściciela
  (Commodore International Corp. od 31.07.2025) i jego FAQ toleruje projekty fanowskie,
  jeśli są *„clearly unofficial"* — dlatego rodziny nazywają się `Ogonek 64`,
  a nie nazwą handlową.
