package main

import (
  "crypto/sha256"
  "encoding/hex"
  "encoding/json"
  "io"
  "net/http"
)

type Health struct { Service string `json:"service"`; Runtime string `json:"runtime"`; Policy string `json:"policy"` }

func main() {
  http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { if r.Method != http.MethodGet { http.Error(w,"method_not_allowed",405); return }; w.Header().Set("Content-Type","application/json"); _=json.NewEncoder(w).Encode(Health{"noryx7-jarvis-gateway","ready","deny-by-default"}) })
  http.HandleFunc("/digest", func(w http.ResponseWriter, r *http.Request) { if r.Method != http.MethodPost { http.Error(w,"method_not_allowed",405); return }; b,_:=io.ReadAll(r.Body); sum:=sha256.Sum256(b); _=json.NewEncoder(w).Encode(map[string]string{"sha256":hex.EncodeToString(sum[:])}) })
  _ = http.ListenAndServe(":8080", nil)
}
