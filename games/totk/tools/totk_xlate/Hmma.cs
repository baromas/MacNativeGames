// Adapted from MD5Visual/MacNativeGames a57fb5c2, matching nxnative hmma_msl. MIT; see THIRD_PARTY_NOTICES.md.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
internal static class Hmma
{
    const string HmmaBody = "\n{\n" +
        "    threadgroup uint* s = &%(scr)s[uint(%(blk)s)];\n" +
        "    uint g = uint(%(lane)s) >> 2, t = uint(%(lane)s) & 3;\n" +
        "    s[g * 8 + t] = uint(%(a0)s); s[(g + 8) * 8 + t] = uint(%(a1)s); s[g * 8 + 4 + t] = uint(%(a2)s); s[(g + 8) * 8 + 4 + t] = uint(%(a3)s);\n" +
        "    s[128 + g * 8 + t] = uint(%(b0)s); s[128 + g * 8 + 4 + t] = uint(%(b1)s);\n" +
        "    s[192 + g * 4 + t] = uint(%(acc0)s); s[192 + (g + 8) * 4 + t] = uint(%(acc1)s);\n" +
        "    simdgroup_barrier(mem_flags::mem_threadgroup);\n" +
        "    threadgroup half* h = (threadgroup half*)s;\n" +
        "    simdgroup_half8x8 a00, a01, a10, a11, b0, b1, c0, c1;\n" +
        "    simdgroup_load(a00, h, 16, ulong2(0, 0)); simdgroup_load(a01, h, 16, ulong2(8, 0)); simdgroup_load(a10, h, 16, ulong2(0, 8)); simdgroup_load(a11, h, 16, ulong2(8, 8));\n" +
        "    simdgroup_load(b0, h + 256, 16, ulong2(0, 0), true); simdgroup_load(b1, h + 256, 16, ulong2(8, 0), true);\n" +
        "    simdgroup_load(c0, h + 384, 8, ulong2(0, 0)); simdgroup_load(c1, h + 384, 8, ulong2(0, 8));\n" +
        "    simdgroup_multiply_accumulate(c0, a00, b0, c0); simdgroup_multiply_accumulate(c0, a01, b1, c0);\n" +
        "    simdgroup_multiply_accumulate(c1, a10, b0, c1); simdgroup_multiply_accumulate(c1, a11, b1, c1);\n" +
        "    simdgroup_store(c0, h + 384, 8, ulong2(0, 0)); simdgroup_store(c1, h + 384, 8, ulong2(0, 8));\n" +
        "    simdgroup_barrier(mem_flags::mem_threadgroup);\n" +
        "    uint d0 = s[192 + g * 4 + t], d1 = s[192 + (g + 8) * 4 + t];\n" +
        "    simdgroup_barrier(mem_flags::mem_threadgroup);\n" +
        "    %(d1)s = as_type<%(dt)s>(d1);\n" +
        "    return as_type<%(rt)s>(d0);\n" +
        "}\n";
    public static string Rewrite(string src)
    {
        var m = Regex.Match(src, @"\n(\w+) dmsh_hmma16816_f16\(([^)]*)\)\n\{");
        if (!m.Success) { if (src.Contains("dmsh_hmma16816_f16")) throw new InvalidOperationException("HMMA helper signature not recognized"); return src; }
        var ps = new List<string>(); int depth = 0; string cur = "";
        foreach (char ch in m.Groups[2].Value + ",")
        {
            if (ch == '<') depth++; else if (ch == '>') depth--;
            if (ch == ',' && depth == 0) { ps.Add(cur.Trim()); cur = ""; } else cur += ch;
        }
        var scr = ps.Where(x => x.StartsWith("threadgroup ")).ToList();
        var plain = ps.Where(x => !x.StartsWith("threadgroup ")).ToList();
        string Bad() => "dmsh_hmma16816_f16: unexpected parameters " + m.Groups[2].Value.Substring(0, Math.Min(200, m.Groups[2].Value.Length));
        if (scr.Count != 1 || plain.Count != 11) throw new InvalidOperationException(Bad());
        string Name(string x) { var mm = Regex.Match(x, @"(\w+)$"); if (!mm.Success) throw new InvalidOperationException(Bad()); return mm.Groups[1].Value; }
        var dtm = Regex.Match(plain[10], @"^thread (\w+)&"); if (!dtm.Success) throw new InvalidOperationException(Bad());
        string prefix = "totk_hmma_";
        while (src.Contains(prefix)) prefix += "_";
        string body = Regex.Replace(HmmaBody, @"%\(\w+\)s|\b(?:s|g|t|h|a00|a01|a10|a11|b0|b1|c0|c1|d0|d1)\b", m => m.Value.StartsWith("%(") ? m.Value : prefix + m.Value);
        string[] keys = ["lane", "blk", "a0", "a1", "a2", "a3", "b0", "b1", "acc0", "acc1", "d1"];
        for (int i = 0; i < keys.Length; i++) body = body.Replace("%(" + keys[i] + ")s", Name(plain[i]));
        body = body.Replace("%(scr)s", Name(scr[0])).Replace("%(dt)s", dtm.Groups[1].Value).Replace("%(rt)s", m.Groups[1].Value);
        int start = m.Index + m.Length - 1; depth = 0; int end = -1;
        for (int i = start; i < src.Length; i++)
        {
            if (src[i] == '{') depth++; else if (src[i] == '}') depth--;
            if (depth == 0) { end = i; break; }
        }
        if (end < 0) throw new InvalidOperationException("dmsh_hmma16816_f16: body not closed");
        return src.Substring(0, start) + body + src.Substring(end + 1);
    }
}
