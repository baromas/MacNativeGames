// MIT adaptation of Kolkka/MacNativeGames f70b81ba, NVN2 base-instance lowering.
using System;
using System.Text.RegularExpressions;

static class ShaderBaseInstance
{
    public static string Rewrite(string src)
    {
        const string word = "(*spvDescriptorSet0.vp_c0)._m0[100].y";
        if (!src.Contains(word, StringComparison.Ordinal)) return src;
        // Only this scalar is established. A read of another lane remains unfillable.
        string s = src.Replace(word, "as_type<float>(int(mng_base_instance))", StringComparison.Ordinal);
        if (s.Contains("vp_c0)._m0[100]", StringComparison.Ordinal)) return src;
        Match entry = Regex.Match(s, @"\bvertex\s+\w+\s+\w+\s*\(");
        if (!entry.Success) return src;
        // Balance parentheses: Metal argument attributes and templates contain nested pairs.
        int depth = 1, end = entry.Index + entry.Length;
        for (; end < s.Length && depth != 0; end++)
        {
            if (s[end] == '(') depth++;
            if (s[end] == ')') depth--;
        }
        if (depth != 0) return src;
        int bodyStart = s.IndexOf('{', end), bodyEnd = bodyStart + 1, braces = 1;
        if (bodyStart < 0) return src;
        for (; bodyEnd < s.Length && braces != 0; bodyEnd++)
        {
            if (s[bodyEnd] == '{') braces++;
            if (s[bodyEnd] == '}') braces--;
        }
        if (braces != 0 || s.Substring(0, bodyStart).Contains("mng_base_instance", StringComparison.Ordinal) ||
            s.Substring(bodyEnd).Contains("mng_base_instance", StringComparison.Ordinal)) return src;
        string prefix = s.Substring(entry.Index + entry.Length, end - entry.Index - entry.Length - 1).Trim();
        Match builtin = Regex.Match(prefix, @"\b(?:uint|int)\s+(\w+)\s*\[\[\s*base_instance\s*\]\]");
        if (builtin.Success) return s.Replace("mng_base_instance", builtin.Groups[1].Value, StringComparison.Ordinal);
        if (prefix.Contains("base_instance", StringComparison.Ordinal)) return src;
        return s.Insert(end - 1, (prefix.Length == 0 ? "" : ", ") + "uint mng_base_instance [[base_instance]]");
    }
}
