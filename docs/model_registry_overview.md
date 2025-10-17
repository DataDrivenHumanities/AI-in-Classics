# Model registry: what changed and why

This document is written for teammates who do not work with code every day.
It explains, in plain language, how the recent "model registry" work affects
our app and what you need to do in the future.

## 1. Why we made this change

Previously, every time we wanted to add or swap a large-language-model (LLM)
in the app, a developer had to edit Python files. That meant waiting for a
code change, reviews, and deployments. The goal of the registry is to make
that process as simple as editing a short list, without touching the app
logic.

## 2. The new building blocks

* **`model_registry.json`** – a tiny text file that lists the models we care
  about. Each entry includes the model's name, whether it is ready for use,
  and a short description for teammates.
* **`model_registry.py`** – a helper that reads the file above and serves the
  information to the rest of the app.
* **Streamlit sidebar update** – the menu on the left side of the app now
  reads from the registry file. Whatever is listed there becomes selectable in
  the app, and the upcoming models are labelled as "coming soon".

## 3. Step-by-step: adding a new model

1. **Open the registry file**: in your editor, open
   `src/app/model_registry.json`. You will see a list (`[]`) of model entries.
2. **Copy an existing entry**: duplicate one of the objects and change the
   values. Each entry uses this shape:

   ```json
   {
     "tag": "latin-latest",
     "label": "Latin production (v4)",
     "available": true,
     "is_default": false,
     "description": "High-accuracy Latin analysis model"
   }
   ```

   * `tag` is the short handle the backend expects.
   * `label` is what teammates will read in the app sidebar.
   * `available` should be `true` only when the model is safe to use.
   * `is_default` should be `true` for exactly one model in the list (usually
     your new model once it launches).
   * `description` is optional but helps others understand what changed.
3. **Save the file**: nothing else is required. When the app starts, the
   Streamlit sidebar reads this file and automatically shows the new entry. If
   `available` is `false`, it will appear as "coming soon" so teammates know
   it exists but cannot select it yet.

For advanced scenarios you can point the app at a completely different registry
by setting the `TP_MODEL_REGISTRY` environment variable before launching it.

## 4. What stays the same

* The rest of the app still behaves exactly as before; we only changed how the
  list of models is provided.
* Advanced users can still override the model at runtime with the existing
  `TP_MODEL` environment variable.

## 5. How this differs from the old workflow

| Task | Before the registry | Now |
| --- | --- | --- |
| Add a new model | Ask a developer to edit Python files, wait for code review and deployment. | Edit `model_registry.json` yourself; the app picks it up on the next launch. |
| Change the default model | Update hard-coded defaults in multiple modules. | Flip `"is_default": true` on the correct registry entry. |
| Preview an upcoming model | Keep side-channel notes or comment code so people know what is coming. | Add the model with `"available": false`; it shows up as "coming soon" automatically. |

If anything here is unclear, please reach out—we can walk through an example
live.
