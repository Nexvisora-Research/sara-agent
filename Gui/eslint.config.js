module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint"],
  extends: ["eslint:recommended", "plugin:@typescript-eslint/recommended"],
  ignorePatterns: ["dist/", "release/", "node_modules/"],
  rules: { "@typescript-eslint/no-explicit-any": "warn", "@typescript-eslint/no-unused-vars": "warn" },
};