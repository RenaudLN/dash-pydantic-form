window.dash_clientside = window.dash_clientside || {}

function waitForElem(id) {
  return new Promise(resolve => {
      if (document.getElementById(id)) {
          return resolve(document.getElementById(id));
      }

      const observer = new MutationObserver(mutations => {
          if (document.getElementById(id)) {
              observer.disconnect();
              resolve(document.getElementById(id));
          }
      });

      // If you get "parameter 1 is not of type 'Node'" error, see https://stackoverflow.com/a/77855838/492336
      observer.observe(document.body, {
          childList: true,
          subtree: true
      });
  });
}

dash_clientside.pydf = {
  getValues: () => {
    const inputs = dash_clientside.callback_context.inputs_list[0].concat(dash_clientside.callback_context.inputs_list[1])
    const dictItemKeys = dash_clientside.callback_context.inputs_list[2].reduce((current, x) => {
      current[`${x.id.parent}:${x.id.field}:${x.id.meta}`.replace(/^:/, "")] = x.value
      return current
    }, {})
    const hiddenPaths = dash_clientside.callback_context.inputs_list[3]
      .filter(x => x.value.display == "none")
      .map(x => x.id.meta.split("|")[0])
    const formData = inputs.reduce((acc, val) => {
        const key = `${val.id.parent}:${val.id.field}`.replace(/^:/, "")
        if (hiddenPaths.some(p => key.startsWith(p))) return acc
        const parts = key.split(":")
        let pointer = acc
        const matchingDictKeys = Object.fromEntries(
          Object.entries(dictItemKeys)
          .filter(entry => key.startsWith(entry[0]))
          .map(([k, v]) => [k.split(":").length, v])
        )
        parts.forEach((part, i) => {
            // Update the list key if it is a dict entry
            const nextMatch = Number(Object.keys(matchingDictKeys).sort().filter(x => x >= i + 1)[0] || -1)
            if (i + 1 == nextMatch) {
              part = matchingDictKeys[i + 1] || part
            }
            if (i === parts.length - 1) {
              pointer[part] = val.value
            } else {
                const prt = i + 1 !== nextMatch && /^\d+$/.test(part) ? Number(part) : part
                if (!pointer[prt]) {
                    pointer[prt] = i + 2 !== nextMatch && /^\d+$/.test(parts[i + 1]) ? [] : {}
                }
                pointer = pointer[prt]
            }
        })
        return acc
    }, {})
    return formData
  },
  updateFieldVisibility: (value, checked) => {

    const checkVisibility = (value, operator, expectedValue) => {
        switch (operator) {
            case "==":
                return value == expectedValue
            case "!=":
                return value != expectedValue
            case "in":
                return expectedValue.includes(value)
            case "not in":
                return !expectedValue.includes(value)
            case "array_contains":
                return value.includes(expectedValue)
            case "array_contains_any":
                return value.some(v => expectedValue.includes(v))
            default:
                return true
        }
    }

    const newStyles = []
    let actualValue
    if (value.length > 0) {
        actualValue = value[0]
    } else {
        actualValue = checked[0]
    }
    // Iterate through each visibility wrapper and check its dependent field value
    // to update its display property
    dash_clientside.callback_context.states_list[0].forEach(state => {
        let [_f, operator, expectedValue] = state.id.meta.split("|")
        expectedValue = JSON.parse(expectedValue)
        newStyles.push({
            ...state.value,
            display: checkVisibility(actualValue, operator, expectedValue) ? null : "none",
        })
    })

    return newStyles
  },
  sync: x => x,
  syncTrue: x => !!x,
  syncFalse: x => !x,
  updateModalTitle: (val, id) => {
    const out = val != null ? String(val) : dash_clientside.no_update
    if (typeof out === "string") {
      dash_clientside.set_props(
        {...id, component: "_pydf-list-field-modal-text"},
        {"children": out}
      )
    }
    return out
  },
  updateAccordionTitle: (val) => {
    return val != null ? String(val) : dash_clientside.no_update
  },
  syncTableJson: (rowData) => {
    return rowData.filter(row => Object.values(row).some(x => x != null))
  },
  stepsClickListener: (id) => {
    const strId = JSON.stringify(id, Object.keys(id).sort())
    waitForElem(strId).then((elem) => {
      const steps = elem.children[0].children
      for (let i = 0; i < steps.length; i++) {
          const child = steps[i]
          child.addEventListener("click", event => {
              dash_clientside.set_props(id, {active: i})
          })
      }
    })

    return dash_clientside.no_update
  },
  stepsDisable: (active, nSteps) => [active === 0, active === nSteps],
  stepsPreviousNext: (_t1, _t2, active, nSteps) => {
    const trigger = dash_clientside.callback_context.triggered
    if (!trigger || trigger.length === 0) return dash_clientside.no_update
    const trigger_id = JSON.parse(trigger[0].prop_id.split(".")[0])
    if (trigger_id.part.includes("next")) return Math.min(active + 1, nSteps)
    if (trigger_id.part.includes("previous")) return Math.max(0, active - 1)
    return dash_clientside.no_update
  },
  listenToSubmit: (id, enterSubmits) => {
    const el = document.getElementById(
      JSON.stringify(id, Object.keys(id).sort())
    )
    if (el && enterSubmits) {
      el.addEventListener("keypress", event => {
          if (event.key === "Enter" && event.target.tagName === "INPUT") {
              event.preventDefault()
              dash_clientside.set_props(id, {"data-submit": 1})
          }
      })
    }
    return dash_clientside.no_update
  },
  displayErrors: (errors, ids) => {
    if (!errors) return Array(ids.length).fill(null)

    return ids.map(id => {
      const fullPath = id.parent ? `${id.parent}:${id.field}` : id.field
      return errors[fullPath]
    })
  },
  addToList: (trigger, current, template) => {
    if (trigger == null) return dash_clientside.no_update
    const path = getFullpath(
      dash_clientside.callback_context.triggered_id.parent,
      dash_clientside.callback_context.triggered_id.field,
    ).replaceAll(":", "|")
    const templateCopy = JSON.parse(template.replaceAll(`{{${path}}}`, String(current.length)))
    if (templateCopy.type == "AccordionItem") {
      templateCopy.props.value = `uuid:${uuid4()}`
    }
    return [...current, templateCopy]
  },
  deleteFromList: (trigger, current) => {
    // return dash_clientside.no_update
    if (trigger.every(t => t == null)) return dash_clientside.no_update
    const idx = Number(dash_clientside.callback_context.triggered_id.meta)
    const path = getFullpath(
      dash_clientside.callback_context.triggered_id.parent,
      dash_clientside.callback_context.triggered_id.field,
    )
    const newChildren = current.filter((_, i) => i !== idx)
    return newChildren.map((child, i) => updateModelListIds(child, path, i))
  },
  convertQuantityUnit: (newUnit, value, currentUnit, conversions) => {
    if (value == null) return dash_clientside.no_update
    const [rateFrom, baseFrom] = conversions[currentUnit]
    const [rateTo, baseTo] = conversions[newUnit]
    return [((value * rateFrom + baseFrom) - baseTo) / rateTo, newUnit]
  },
  showPathFieldSkeletons: (n) => {
    if (!n) return dash_clientside.no_update

    const skeleton = (props) => ({
      namespace: "dash_mantine_components",
      type: "Skeleton",
      props: {height: 26, ...props},
    })
    const breadcrumbs = {
      namespace: "dash_mantine_components",
      type: "Breadcrumbs",
      props: {
        children: skeleton({width: 120}),
        mb: "1rem",
      },
    }
    const id = dash_clientside.callback_context.inputs_list[0].id
    return [
      !!n,
      {
        namespace: "dash_mantine_components",
        type: "Stack",
        props: {
          children: [breadcrumbs, ...Array(5).fill(0).map((_, idx) => skeleton({width: 150 + (idx % 2) * 32}))],
          gap: "0.25rem",
          align: "start",
          id: {
            ...id,
            component: "_pydf-path-field-filetree",
          },
        }
      }
    ]
  },
  updatePathFieldValue: (_trigger, globs, config, current) => {
    const t = dash_clientside.callback_context.triggered
    if (!t || t.length === 0 || t[0].value == null) return [
      dash_clientside.no_update,
      dash_clientside.no_update,
      dash_clientside.no_update,
    ]
    const t_id = JSON.parse(t[0].prop_id.split('.')[0])

    let path = ""
    if (t_id.path) {
      path = t_id.path.replaceAll("||", ".")
    } else if (typeof current === "string") {
      path = current
    }

    const prefix = config.value_includes_prefix ? `${config.prefix.replace(/\/+$/, "")}/` : ""

    if (t_id.component.includes("glob")) {
      return [dash_clientside.no_update, `${prefix}${path}/${globs[0]}`, dash_clientside.no_update]
    }
    if (config.path_type === "glob") {
      return [false, `${prefix}${path}/${globs[0]}`, `${prefix}${path}`]
    }
    return [false, `${prefix}${path}`, `${prefix}${path}`]
  }
}

// Return a : separated string of the args
const getFullpath = (...args) => {
  return args.filter(x => x != null && x !== "").join(":")
}

const uuid4 = () => {
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
    (+c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> +c / 4).toString(16)
  );
}

const updateModelListIds = (child, path, newIdx) => {
  if (typeof child !== 'object' || child === null) return child
  Object.entries(child).forEach(([key, val]) => {
    if (key === "id" && typeof val === "object" && val.parent != null) {
      val.parent = val.parent.replace(new RegExp(`${path}:(\\d+)`), `${path}:${newIdx}`)
      if (val.parent === path && /\d+/.test(String(val.field))) {
        val.field = newIdx
      }
      if (getFullpath(val.parent, val.field) === path && /\d+/.test(String(val.meta))) {
        val.meta = newIdx
      }
    } else if (key === "title" && typeof val === "string") {
      child[key] = val.replace(new RegExp(`${path}:(\\d+)`), `${path}:${newIdx}`)
    } else if (typeof val === "string" && val.startsWith("uuid:")) {
      child[key] = `uuid:${uuid4()}`
    } else if (typeof val === "object") {
      updateModelListIds(val, path, newIdx)
    } else if (Array.isArray(val)) {
      val.forEach(item => updateModelListIds(item, path, newIdx))
    }
  })
  return child
}
