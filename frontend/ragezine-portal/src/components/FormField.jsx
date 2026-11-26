import { cloneElement, isValidElement, useId } from "react";

import CountrySelect from "./CountrySelect";
import LanguageSelect from "./LanguageSelect";

export default function FormField({ label, children, id, help }) {
  const generatedId = useId();
  const fieldId = id || generatedId;
  const helpId = `${fieldId}-help`;
  const isSingleControl = isValidElement(children) && (
    CountrySelect === children.type || LanguageSelect === children.type ||
    ["input", "select", "textarea"].includes(children.type)
  );

  return (
    <div className="portal-field" role={isSingleControl ? undefined : "group"} aria-labelledby={isSingleControl ? undefined : fieldId}>
      {isSingleControl
        ? <label className="portal-label" htmlFor={fieldId}>{label}</label>
        : <div className="portal-label" id={fieldId}>{label}</div>}
      {isSingleControl ? cloneElement(children, { id: fieldId, ...(help ? { "aria-describedby": helpId } : {}) }) : children}
      {help && <p id={helpId} className="portal-help">{help}</p>}
    </div>
  );
}
