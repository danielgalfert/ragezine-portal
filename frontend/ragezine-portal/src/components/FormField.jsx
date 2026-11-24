import { cloneElement, isValidElement, useId } from "react";

import CountrySelect from "./CountrySelect";
import LanguageSelect from "./LanguageSelect";

export default function FormField({ label, children, id }) {
  const generatedId = useId();
  const fieldId = id || generatedId;
  const isSingleControl = isValidElement(children) && (
    CountrySelect === children.type || LanguageSelect === children.type ||
    ["input", "select", "textarea"].includes(children.type)
  );

  return (
    <div className="portal-field" role={isSingleControl ? undefined : "group"} aria-labelledby={isSingleControl ? undefined : fieldId}>
      {isSingleControl
        ? <label className="portal-label" htmlFor={fieldId}>{label}</label>
        : <div className="portal-label" id={fieldId}>{label}</div>}
      {isSingleControl ? cloneElement(children, { id: fieldId }) : children}
    </div>
  );
}
