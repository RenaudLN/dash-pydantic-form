window.dash_clientside = window.dash_clientside || {};
const PYDF_ROOTMODEL_ROOT = "rootmodel_root_";

dash_clientside.pydf = {
    getValues: (
        _values,
        _checked,
        _keys,
        _visibiilty_wrappers,
        _trigger,
        _delete,
        _add,
        formId,
        storeProgress,
        currentFormData,
        restoreWrapperId,
        restoreBehavior,
        debounce,
        _changesStore={},
    ) => {
        const inputs = dash_clientside.callback_context.inputs_list[0].concat(
            dash_clientside.callback_context.inputs_list[1],
        );
        const dictItemKeys =
            dash_clientside.callback_context.inputs_list[2].reduce(
                (current, x) => {
                    current[
                        `${x.id.parent}:${x.id.field}:${x.id.meta}`.replace(
                            /^:/,
                            "",
                        )
                    ] = x.value;
                    return current;
                },
                {},
            );
        const hiddenPaths = dash_clientside.callback_context.inputs_list[3]
            .filter((x) => x.value.display == "none")
            .map((x) => x.id.meta.split("|")[0]);
        const strId = sortedJson(
            dash_clientside.callback_context.outputs_list[0].id,
        );
        let formData = dataFromInputs(inputs, hiddenPaths, dictItemKeys, formState[strId] || currentFormData);
        if (formData === undefined) {
            return [dash_clientside.no_update, dash_clientside.no_update];
        }
        formState[strId] = formData;

        // Handle the storing/retrieval of form data if requested
        if (
            storeProgress === true ||
            storeProgress === "session" ||
            storeProgress === "local"
        ) {
            const storageKey = `pydfFormData-${sortedJson(dash_clientside.callback_context.outputs_list[0].id)}`;
            const store =
                storeProgress === "session" ? sessionStorage : localStorage;
            // If this is the first time the form is rendered, try retrieving the stored data
            // and update the form if it is different
            if (
                // No data in the ids.main data
                !dash_clientside.callback_context.triggered_id &&
                // And top-level form
                dash_clientside.callback_context.outputs_list[0].id.parent == "" &&
                // And not triggered by data-getvalue
                !(
                    dash_clientside.callback_context.triggered.length > 0 &&
                    dash_clientside.callback_context.triggered[0].prop_id.includes(
                        "getvalue",
                    )
                )
            ) {
                const oldData = store.getItem(storageKey);
                if (oldData && oldData !== sortedJson(formData)) {
                    if (restoreBehavior === "notify") {
                        dash_clientside.set_props(formId, {
                            "data-restored": JSON.parse(oldData),
                        });
                        dash_clientside.set_props(restoreWrapperId, {
                            style: null,
                        });
                        return [dash_clientside.no_update, dash_clientside.no_update];
                    } else if (restoreBehavior === "auto") {
                        dash_clientside.set_props(formId, {
                            "data-update": JSON.parse(oldData),
                        });
                        return [dash_clientside.no_update, dash_clientside.no_update];
                    }
                }
            }
            // Store the latest form data
            store.setItem(storageKey, sortedJson(formData));
        }

        if (dash_clientside.callback_context.triggered_id) {
            const {field, parent} = dash_clientside.callback_context.triggered_id
            if (field && dash_clientside.callback_context.triggered.length === 1) {
                _changesStore[getFullpath(parent, field)] = 1;
            }
        }

        valuesDebounce(dash_clientside.set_props, debounce || 0)(
            dash_clientside.callback_context.outputs_list[0].id,
            { data: formData },
        );

        return [dash_clientside.no_update, _changesStore || {}];
    },
    restoreData: (trigger, data) => {
        if (!data || !trigger) return Array(3).fill(dash_clientside.no_update);
        return [data, { display: "none" }, null];
    },
    cancelRestoreData: (trigger) => {
        if (!trigger) return Array(3).fill(dash_clientside.no_update);
        return [{ display: "none" }, null, 1];
    },
    updateFieldVisibility: (value, checked) => {
        const checkVisibility = (value, operator, expectedValue) => {
            switch (operator) {
                case "==":
                    return value == expectedValue;
                case "!=":
                    return value != expectedValue;
                case "in":
                    return expectedValue.includes(value);
                case "not in":
                    return !expectedValue.includes(value);
                case "array_contains":
                    return value.includes(expectedValue);
                case "array_contains_any":
                    return value.some((v) => expectedValue.includes(v));
                default:
                    return true;
            }
        };

        const newStyles = [];
        let actualValue;
        if (value.length > 0) {
            actualValue = value[0];
        } else {
            actualValue = checked[0];
        }
        // Iterate through each visibility wrapper and check its dependent field value
        // to update its display property
        dash_clientside.callback_context.states_list[0].forEach((state) => {
            let [_f, operator, expectedValue] = state.id.meta.split("|");
            expectedValue = JSON.parse(expectedValue);
            newStyles.push({
                ...state.value,
                display: checkVisibility(actualValue, operator, expectedValue)
                    ? null
                    : "none",
            });
        });

        return newStyles;
    },
    sync: (x) => x,
    syncTrue: (x) => !!x,
    syncFalse: (x) => !x,
    updateModalTitle: (val, id) => {
        const out = val != null ? String(val) : dash_clientside.no_update;
        if (typeof out === "string") {
            dash_clientside.set_props(
                { ...id, component: "_pydf-list-field-modal-text" },
                { children: out },
            );
        }
        return out;
    },
    updateAccordionTitle: (val) => {
        return val != null ? String(val) : dash_clientside.no_update;
    },
    syncTableJson: (rowData) => {
        return rowData.filter((row) =>
            Object.values(row).some((x) => x != null),
        );
    },
    stepsDisable: (active, nSteps) => [active === 0, active === nSteps],
    stepsPreviousNext: (_t1, _t2, active, nSteps) => {
        const trigger = dash_clientside.callback_context.triggered;
        if (!trigger || trigger.length === 0) return dash_clientside.no_update;
        const trigger_id = JSON.parse(trigger[0].prop_id.split(".")[0]);
        if (trigger_id.part.includes("next"))
            return Math.min(active + 1, nSteps);
        if (trigger_id.part.includes("previous"))
            return Math.max(0, active - 1);
        return dash_clientside.no_update;
    },
    listenToSubmit: (id, enterSubmits) => {
        const el = document.getElementById(
            JSON.stringify(id, Object.keys(id).sort()),
        );
        if (el && enterSubmits) {
            el.addEventListener("keypress", (event) => {
                if (event.key === "Enter" && event.target.tagName === "INPUT") {
                    event.preventDefault();
                    dash_clientside.set_props(id, { "data-submit": 1 });
                }
            });
        }
        return dash_clientside.no_update;
    },
    displayErrors: (errors, ids) => {
        if (!errors) return Array(ids.length).fill(null);

        return ids.map((id) => {
            const fullPath = getFullpath(id.parent, id.field).replaceAll(
                `${PYDF_ROOTMODEL_ROOT}:`,
                "",
            );
            return errors[fullPath];
        });
    },
    addToList: (trigger, current, template) => {
        if (trigger == null) return dash_clientside.no_update;
        const path = getFullpath(
            dash_clientside.callback_context.triggered_id.parent,
            dash_clientside.callback_context.triggered_id.field,
        ).replaceAll(":", "|");
        const templateCopy = JSON.parse(
            template.replaceAll(`{{${path}}}`, String(current.length)),
        );
        if (templateCopy.type == "AccordionItem") {
            templateCopy.props.value = `uuid:${uuid4()}`;
            dash_clientside.set_props(
                dash_clientside.callback_context.outputs_list.id,
                { value: templateCopy.props.value },
            );
        }
        const firstValueField = findFirstValueField(templateCopy);
        if (firstValueField) {
            waitForElem(stringifyId(firstValueField)).then((el) => {
                el.focus();
            });
        }
        return [...current, templateCopy];
    },
    deleteFromList: (trigger, current) => {
        // return dash_clientside.no_update
        if (trigger.every((t) => t == null)) return dash_clientside.no_update;
        const idx = Number(dash_clientside.callback_context.triggered_id.meta);
        const path = getFullpath(
            dash_clientside.callback_context.triggered_id.parent,
            dash_clientside.callback_context.triggered_id.field,
        );
        const newChildren = current.filter((_, i) => i !== idx);
        return newChildren.map((child, i) =>
            updateModelListIds(child, path, i),
        );
    },
    convertQuantityUnit: (newUnit, value, currentUnit, conversions) => {
        if (value == null) return dash_clientside.no_update;
        const [rateFrom, baseFrom] = conversions[currentUnit];
        const [rateTo, baseTo] = conversions[newUnit];
        return [(value * rateFrom + baseFrom - baseTo) / rateTo, newUnit];
    },
    showPathFieldSkeletons: (n) => {
        if (!n) return [dash_clientside.no_update, dash_clientside.no_update];

        const skeleton = (props) => ({
            namespace: "dash_mantine_components",
            type: "Skeleton",
            props: { height: 26, ...props },
        });
        const breadcrumbs = {
            namespace: "dash_mantine_components",
            type: "Breadcrumbs",
            props: {
                children: skeleton({ width: 120 }),
                mb: "1rem",
            },
        };
        const id = dash_clientside.callback_context.inputs_list[0].id;
        return [
            !!n,
            {
                namespace: "dash_mantine_components",
                type: "Stack",
                props: {
                    children: [
                        breadcrumbs,
                        ...Array(5)
                            .fill(0)
                            .map((_, idx) =>
                                skeleton({ width: 150 + (idx % 2) * 32 }),
                            ),
                    ],
                    gap: "0.25rem",
                    align: "start",
                    id: {
                        ...id,
                        component: "_pydf-path-field-filetree",
                    },
                },
            },
        ];
    },
    updatePathFieldValue: (_trigger, globs, config, current) => {
        const t = dash_clientside.callback_context.triggered;
        if (!t || t.length === 0 || t[0].value == null)
            return [
                dash_clientside.no_update,
                dash_clientside.no_update,
                dash_clientside.no_update,
            ];
        const t_id = JSON.parse(t[0].prop_id.split(".")[0]);

        let path = "";
        if (t_id.path) {
            path = t_id.path.replaceAll("||", ".");
        } else if (typeof current === "string") {
            path = current;
        }

        const prefix = config.value_includes_prefix
            ? `${config.prefix.replace(/\/+$/, "")}/`
            : "";

        if (t_id.component.includes("glob")) {
            return [
                dash_clientside.no_update,
                `${prefix}${path}/${globs[0]}`,
                dash_clientside.no_update,
            ];
        }
        if (config.path_type === "glob") {
            return [false, `${prefix}${path}/${globs[0]}`, `${prefix}${path}`];
        }
        return [false, `${prefix}${path}`, `${prefix}${path}`];
    },
    tableAddRow: (trigger, columnDefs) => {
        if (!trigger) return dash_clientside.no_update;

        return {
            add: [
                Object.fromEntries(
                    columnDefs
                        .filter((colDef) => !!colDef.field)
                        .map((colDef) => [colDef.field, colDef.default_value]),
                ),
            ],
        };
    },
};

let valuesTimer = {};
let formState = {};
function valuesDebounce(func, timeout) {
    return (...args) => {
        const strId = sortedJson(args[0]);
        if (!!valuesTimer[strId]) {
            clearTimeout(valuesTimer[strId]);
        }
        valuesTimer[strId] = setTimeout(() => {
            func.apply(this, args);
            delete formState[strId];
        }, timeout);
    };
}

// Make sure lodash is available as _
function dataFromInputs(inputs, hiddenPaths, dictItemKeys, currentFormData) {
    const id = dash_clientside.callback_context.triggered_id;
    if (inputs.length === 0) {
        return _.omitBy(currentFormData, _.isEmpty) || {}
    }

    function fixPathKeys(parts) {
        for (let i = 0; i < parts.length; i++) {
            const dictKey = parts.slice(0, i + 1).join(":");
            if (dictItemKeys.hasOwnProperty(dictKey)) {
                parts[i] = dictItemKeys[dictKey];
            } else {
                parts[i] = /^\d+$/.test(parts[i]) ? Number(parts[i]) : parts[i]
            }
        }
        return parts;
    }

    const firstKey = getFullpath(inputs[0].id.parent, inputs[0].id.field);
    const startsWithArray =
        firstKey.startsWith(`${PYDF_ROOTMODEL_ROOT}:`) &&
        firstKey.split(":").length > 1 &&
        /^\d+$/.test(firstKey.split(":")[1]) &&
        !Object.keys(dictItemKeys).includes(
            firstKey.split(":").slice(0, 2).join(":"),
        );

    let formData = currentFormData ? _.cloneDeep(currentFormData) : (startsWithArray ? [] : {});
    if (_.isEmpty(formData)) {
        formData = startsWithArray ? [] : {};
    }

    if (id) {
        var path = getFullpath(id.parent, id.field).split(':').filter((p) => p !== PYDF_ROOTMODEL_ROOT);
        if (id.meta && id.meta != 'discriminator') {
            path.push(id.meta)
        }
        path = fixPathKeys(path)
        if (id.component === "_pydf-list-field-delete") {
            if (dash_clientside.callback_context.triggered[0].value === 1) {
                if (typeof path[path.length - 1] === "number") {
                    path = path.slice(0, -1);
                }
                if (path.length === 0) {
                    oldList = formData;
                } else {
                    oldList = _.get(formData, path, []);
                }
                if (Array.isArray(oldList)) {
                    const newList = oldList.slice(0, id.meta).concat(oldList.slice(id.meta + 1));
                    if (newList.length > 0) {
                        _.set(formData, path, newList);
                    } else {
                        _.unset(formData, path);
                    }
                } else {
                    _.unset(formData, path);
                }
                return formData;
            }
        }
        if (id && dictItemKeys.hasOwnProperty(`${getFullpath(id.parent, id.field)}:${id.meta}`)) {
            _.unset(formData, path.slice(0, -1));
        }
    }
    for (const val of inputs) {
        let key = getFullpath(val.id.parent, val.id.field);
        if (hiddenPaths.some((p) => key.startsWith(`${p}:`) || key === p)) {
            continue;
        }
        var parts = key.split(":").filter((p) => p !== PYDF_ROOTMODEL_ROOT);
        // Handle dictItemKeys replacement
        if (val.id.meta && val.id.meta != 'discriminator') {
            parts.push(val.id.meta)
        }
        parts = fixPathKeys(parts);
        if (dictItemKeys.hasOwnProperty(key)) {
            parts = parts.slice(0, -1).concat([dictItemKeys[key]]);
        }
        _.set(formData, parts, val.value);
    }
    return formData;
}


function waitForElem(id) {
    return new Promise((resolve) => {
        if (document.getElementById(id)) {
            return resolve(document.getElementById(id));
        }

        const observer = new MutationObserver((mutations) => {
            if (document.getElementById(id)) {
                observer.disconnect();
                resolve(document.getElementById(id));
            }
        });

        // If you get "parameter 1 is not of type 'Node'" error, see https://stackoverflow.com/a/77855838/492336
        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });
    });
}

const sortedJson = (obj) => {
    const allKeys = new Set();
    JSON.stringify(obj, (key, value) => (allKeys.add(key), value));
    return JSON.stringify(obj, Array.from(allKeys).sort());
};

const stringifyId = (id) => {
    if (window.dash_component_api && window.dash_component_api.stringifyId) {
        return window.dash_component_api.stringifyId(id);
    }
    if (typeof id === "object") {
        return sortedJson(id);
    }
    return id;
}

// Return a : separated string of the args
const getFullpath = (...args) => {
    return args.filter((x) => x != null && x !== "").join(":");
};

const uuid4 = () => {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) =>
        (
            +c ^
            (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))
        ).toString(16),
    );
};

const updateModelListIds = (child, path, newIdx) => {
    if (typeof child !== "object" || child === null) return child;
    Object.entries(child).forEach(([key, val]) => {
        if (key === "id" && typeof val === "object" && val.parent != null) {
            val.parent = val.parent.replace(
                new RegExp(`${path}:(\\d+)`),
                `${path}:${newIdx}`,
            );
            if (val.parent === path && /\d+/.test(String(val.field))) {
                val.field = newIdx;
            }
            if (
                getFullpath(val.parent, val.field) === path &&
                /\d+/.test(String(val.meta))
            ) {
                val.meta = newIdx;
            }
        } else if (key === "title" && typeof val === "string") {
            child[key] = val.replace(
                new RegExp(`${path}:(\\d+)`),
                `${path}:${newIdx}`,
            );
        } else if (typeof val === "string" && val.startsWith("uuid:")) {
            child[key] = `uuid:${uuid4()}`;
        } else if (typeof val === "object") {
            updateModelListIds(val, path, newIdx);
        } else if (Array.isArray(val)) {
            val.forEach((item) => updateModelListIds(item, path, newIdx));
        }
    });
    return child;
};

function findFirstValueField(obj) {
    if (
        obj.props &&
        obj.props.id &&
        obj.props.id.component === "_pydf-value-field"
    )
        return obj.props.id;
    if (obj.props && Array.isArray(obj.props?.children)) {
        for (const child of obj.props.children) {
            const out = findFirstValueField(child);
            if (!!out) return out;
        }
    } else if (obj.props && obj.props?.children) {
        return findFirstValueField(obj.props.children);
    }
    return null;
}
