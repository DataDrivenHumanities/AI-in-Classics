# How to clean XML manually

1. Scan and remove single tags (those that do not come with a closing tag) that interrupt text flow in `<div>` and `<p>` tags. For example, remove `<lb/>` below. Notice that `<pb/>` tag does not interrupt the flow of text content and stays. In fact, that tag stands for *page beginning* and provides useful metadata, page number to be specific.

 ```
 <div type="textpart" subtype="chapter" n="1">
                    <pb n="224"/>
                    <head>ΑΝΩΝΥΜΟΥ
                        ΑΝΑΜΕΤΡΗΣΙΣ ΤΗΣ ΟΙΚΟΥΜΕΝΗΣ ΗΑΣ ΗΕ
                        ΚΑΤΑ ΣΥΝΟΨΙΝ.</head>

                        <div type="textpart" subtype="paragraph" n="1"><p>1. Χρὴ γινώσκειν ὅτι πάσης τῆς γῆς ὁ περίμετρος.
                        στάδιά ἐστι δισχίλια καὶ μυριάδες εἴκοσι πέντε· μῆκος
                        δὲ τῆς ἡμετέρας οἰκουμένης ἀπὸ στόματος Γάγγου ἕως
                        Γαδείρων στάδια ὀκτακισμύρια τρισχίλια ὀκ τακόσια·
                        <lb n="5"/> τὸ δὲ πλάτος ἀπὸ τῆς Αἰθιοπικῆς θαλάσσης ἕως τοῦ
                        Τανάϊδος ποταμοῦ στάδια τρισμύρια πεντακισχίλια
                        τὸ δὲ μεταξὺ Εὐφράτου καὶ Τίγριδος ποταμοῦ, ὃ καλεῖται
                        Μεσοποτάμιον, διάστημα ἔχει σταδίων τρισχιλίων,
                        Ταύτην τὴν ἀναμέτρησιν πεποίηκεν Ἐρατοσθένης
                        <lb n="10"/> ὁ τῶν ἀρχαίων μαθητικώτατος.</p>
                    
                </div>
 ```

 *BECOMES*

 ```
 <div type="textpart" subtype="chapter" n="1">
                    <pb n="224"/>
                    <head>ΑΝΩΝΥΜΟΥ
                        ΑΝΑΜΕΤΡΗΣΙΣ ΤΗΣ ΟΙΚΟΥΜΕΝΗΣ ΗΑΣ ΗΕ
                        ΚΑΤΑ ΣΥΝΟΨΙΝ.</head>

                        <div type="textpart" subtype="paragraph" n="1"><p>1. Χρὴ γινώσκειν ὅτι πάσης τῆς γῆς ὁ περίμετρος.
                        στάδιά ἐστι δισχίλια καὶ μυριάδες εἴκοσι πέντε· μῆκος
                        δὲ τῆς ἡμετέρας οἰκουμένης ἀπὸ στόματος Γάγγου ἕως
                        Γαδείρων στάδια ὀκτακισμύρια τρισχίλια ὀκ τακόσια·
                        τὸ δὲ πλάτος ἀπὸ τῆς Αἰθιοπικῆς θαλάσσης ἕως τοῦ
                        Τανάϊδος ποταμοῦ στάδια τρισμύρια πεντακισχίλια
                        τὸ δὲ μεταξὺ Εὐφράτου καὶ Τίγριδος ποταμοῦ, ὃ καλεῖται
                        Μεσοποτάμιον, διάστημα ἔχει σταδίων τρισχιλίων,
                        Ταύτην τὴν ἀναμέτρησιν πεποίηκεν Ἐρατοσθένης
                        ὁ τῶν ἀρχαίων μαθητικώτατος.</p>
                    
                </div>
 ```

 2. Scan and remove parts for tags that come in pairs but keep any text content in place e.g. `<supplied> some text </supplied>` given below. In simpler words, make `<supplied>` and `</supplied>` disappear while keeping `some text` where it naturally occurs in the surrounding text.

```
<div type="textpart" subtype="paragraph" n="3"><p>3. Ἀπὸ δὲ τοῦ Ἱεροῦ Διὸς Οὐρίου ἕως Βορυσθένους
                            ποταμοῦ τοῦ καὶ Δανάπρεως καλουμένου στάδια πεντακισχίλια
                            ἑξακόσια, μίλια ἑπτακόσια τεσσαρακονταὲξ
                            ἥμισυ. Ἀπὸ δὲ τοῦ Ἱεροῦ Διὸς Οὐρίου ἕως Πορθμίας
                            <lb n="5"/> πόλεως, τῆς ἐν τέλει τῆς Εὐρώπης τῶν τοῦ Πόντου μερῶν
                            <supplied reason="omitted">τῆς ἐν τῷ στομίῳ</supplied> τῆς Μαιώτιδος λίμνης ἤτοι
                            Βοσπόρου τοῦ Κιμμερίου καλουμένου, στάδια <supplied reason="omitted">μύρια</supplied>
                            χίλια ἑκατόν, μίλια <supplied reason="omitted">χίλια</supplied> τετρακόσια ὀγδοήκοντα.
                            Λέγεται δὲ τῆς Εὐρώπης τῆς Ποντικῆς ὁ περίπλους
                            <lb n="10"/> ἴσος εἶναι τῶ περίπλῳ τῶν τῆς Ἀσίας μερῶν.</p>
```

*BECOMES*

```
<div type="textpart" subtype="paragraph" n="3"><p>3. Ἀπὸ δὲ τοῦ Ἱεροῦ Διὸς Οὐρίου ἕως Βορυσθένους
                            ποταμοῦ τοῦ καὶ Δανάπρεως καλουμένου στάδια πεντακισχίλια
                            ἑξακόσια, μίλια ἑπτακόσια τεσσαρακονταὲξ
                            ἥμισυ. Ἀπὸ δὲ τοῦ Ἱεροῦ Διὸς Οὐρίου ἕως Πορθμίας
                            πόλεως, τῆς ἐν τέλει τῆς Εὐρώπης τῶν τοῦ Πόντου μερῶν
                            τῆς ἐν τῷ στομίῳ τῆς Μαιώτιδος λίμνης ἤτοι
                            Βοσπόρου τοῦ Κιμμερίου καλουμένου, στάδια μύρια
                            χίλια ἑκατόν, μίλια χίλια τετρακόσια ὀγδοήκοντα.
                            Λέγεται δὲ τῆς Εὐρώπης τῆς Ποντικῆς ὁ περίπλους
                            ἴσος εἶναι τῶ περίπλῳ τῶν τῆς Ἀσίας μερῶν.</p>
```

3. If any tag or symbol, especially rare ones, seems uncertain whether to keep or remove, make notice of it and report it.
