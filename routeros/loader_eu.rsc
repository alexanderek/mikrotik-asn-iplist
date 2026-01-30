# RouterOS v7 loader for iplist resources (EU)
# Update URL after repository publish.

:global AddressList "blacklist_eu"
:global resources { cloudflare; }

:if ([:len $resources] = 0) do={
  :log info "iplist: no resources configured for EU"
  :return
}

:local minBytes 200

:foreach resource in=$resources do={
  :do {
    :local url ("https://raw.githubusercontent.com/REPLACE_USER/MikroTik_ASN_IPList/main/dist/" . $resource . ".rsc")
    :local tmpFile ("iplist_" . $resource . ".rsc")

    /tool fetch url=$url mode=https dst-path=$tmpFile keep-result=yes

    :if ([:len [/file find name=$tmpFile]] = 0) do={
      :log warning ("iplist: missing file for " . $resource)
      :error "missing file"
    }

    :local size [/file get $tmpFile size]
    :if ($size < $minBytes) do={
      :log warning ("iplist: file too small for " . $resource . " size=" . $size)
      :error "file too small"
    }

    :local contents [/file get $tmpFile contents]
    :if ([:find $contents "# iplist-rsc v1"] = nil) do={
      :log warning ("iplist: missing sentinel for " . $resource)
      :error "missing sentinel"
    }

    :if ([:find $contents ("# resource=" . $resource)] = nil) do={
      :log warning ("iplist: resource mismatch for " . $resource)
      :error "resource mismatch"
    }

    :local removeLine ("/ip/firewall/address-list remove [find where comment=\"iplist:auto:" . $resource . "\"]")
    :if ([:find $contents $removeLine] = nil) do={
      :log warning ("iplist: remove line missing for " . $resource)
      :error "remove line missing"
    }

    /import file-name=$tmpFile
  } on-error={
    :log warning ("iplist: skipped resource due to error: " . $resource)
  }
}
