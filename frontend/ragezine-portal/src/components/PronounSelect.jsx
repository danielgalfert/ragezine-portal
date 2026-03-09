import Select from "react-select";

export const pronounOptions = [
  { value: "she/her", label: "She / Her" },
  { value: "he/him", label: "He / Him" },
  { value: "they/them", label: "They / Them" },
  { value: "she/they", label: "She / They" },
  { value: "he/they", label: "He / They" },
  { value: "xe/xem", label: "Xe / Xem" },
  { value: "ze/zir", label: "Ze / Zir" },
  { value: "any", label: "Any pronouns" },
  { value: "prefer-not", label: "Prefer not to say" },
  { value: "other", label: "Other" },
];

export default function PronounSelect({
  value,
  onChange,
  name = "pronouns",
  placeholder = "Select pronouns...",
  isClearable = true,
  isMulti = false,
}) {
  const options = pronounOptions;

  const selectedOption = isMulti
    ? options.filter((option) => Array.isArray(value) && value.includes(option.value))
    : options.find((option) => option.value === value) || null;

  function handleChange(selected) {
    if (isMulti) {
      onChange(selected ? selected.map((option) => option.value) : []);
      return;
    }

    onChange(selected ? selected.value : "");
  }

  return (
    <Select
      inputId={name}
      name={name}
      options={options}
      value={selectedOption}
      onChange={handleChange}
      placeholder={placeholder}
      isClearable={isClearable}
      isSearchable={false}
      isMulti={isMulti}
      classNamePrefix="form-select"
    />
  );
}