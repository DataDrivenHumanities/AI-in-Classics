MakeDictCSVs - notebook with code to create the dataframes for functions
    Requires XML files in folder named "Raw_XML"
DictFunctions - has funcitonality of the data
DFManip - using the current DictCSVs to create new ones (data trimming)
In progress -
    Split the parses between greek and latin: they do not have a lang_id tag, so originally files created with them together

    Mood "u" found that isn't listed in the morph_code parsing doc

    Split adj output dict entries based on type of adj? i.e. celer, celeris is different than magnus, magna, magnum

    need to find easy was to differentiate between deponent verbs and impersonal verbs
        current fix: impersonal won't have first person passive indicative form, so check for that

    make edge case for semi-deponent verbs 
    
    figure out way to check for the prefixes on verbs -> co, prae, etc.

    code refactor option - Get FPP from the "lemmas" CSV

    Add checker that we aren't doing ID's that are only in GRK 
Recent fixes - 
    Need to grab FPP from lemmas if not found in parses - i.e. Conflagro (to burn) is in lemmas but not parses - done

    New way to fix enclitics: just use smallest word that fits criteria - WORKS!
